from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/products", tags=["Produtos"])

DbSession = Annotated[Session, Depends(get_db)]


def _get_or_404(db: Session, product_id: int):
    product = crud.get_product(db, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado.")
    return product


def _ensure_category_exists(db: Session, category_id: int) -> None:
    if crud.get_category(db, category_id) is None:
        raise HTTPException(422, "A categoria informada não existe.")


@router.post("", response_model=schemas.ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(data: schemas.ProductCreate, db: DbSession):
    _ensure_category_exists(db, data.category_id)
    return crud.create_product(db, data)


@router.get("", response_model=schemas.Page[schemas.ProductRead])
def list_products(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(description="Busca parcial pelo nome")] = None,
    category_id: int | None = None,
    min_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
):
    items, total = crud.list_products(
        db,
        limit,
        offset,
        search=search,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
    )
    return schemas.Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{product_id}", response_model=schemas.ProductRead)
def get_product(product_id: int, db: DbSession):
    return _get_or_404(db, product_id)


@router.patch("/{product_id}", response_model=schemas.ProductRead)
def update_product(product_id: int, data: schemas.ProductUpdate, db: DbSession):
    product = _get_or_404(db, product_id)
    if data.category_id is not None:
        _ensure_category_exists(db, data.category_id)
    return crud.update_product(db, product, data)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: DbSession):
    crud.delete_product(db, _get_or_404(db, product_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)

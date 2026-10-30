from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db

router = APIRouter(prefix="/products", tags=["Produtos"])

DbSession = Annotated[Session, Depends(get_db)]

_NOT_FOUND_RESPONSE = {status.HTTP_404_NOT_FOUND: {"model": schemas.ErrorResponse}}


def _get_or_404(db: Session, product_id: int) -> models.Product:
    product = crud.get_product(db, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado.")
    return product


def _ensure_category_exists(db: Session, category_id: int) -> None:
    if crud.get_category(db, category_id) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "A categoria informada não existe."
        )


@router.post(
    "",
    response_model=schemas.ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo produto",
)
def create_product(data: schemas.ProductCreate, response: Response, db: DbSession):
    _ensure_category_exists(db, data.category_id)
    try:
        product = crud.create_product(db, data)
    except IntegrityError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "A categoria informada não existe."
        ) from exc
    response.headers["Location"] = f"/products/{product.id}"
    return product


@router.get(
    "",
    response_model=schemas.Page[schemas.ProductRead],
    summary="Lista produtos com filtros, ordenação e paginação",
)
def list_products(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100, description="Itens por página")] = 20,
    offset: Annotated[int, Query(ge=0, description="Deslocamento inicial")] = 0,
    search: Annotated[str | None, Query(description="Busca parcial pelo nome")] = None,
    category_id: Annotated[int | None, Query(description="Filtra pelo ID da categoria")] = None,
    min_price: Annotated[Decimal | None, Query(ge=0, description="Preço mínimo")] = None,
    max_price: Annotated[Decimal | None, Query(ge=0, description="Preço máximo")] = None,
    in_stock: Annotated[
        bool | None, Query(description="Filtra por disponibilidade em estoque")
    ] = None,
    sort_by: Annotated[
        schemas.ProductSortField, Query(description="Campo de ordenação")
    ] = schemas.ProductSortField.ID,
    sort_order: Annotated[
        schemas.SortOrder, Query(description="Direção da ordenação (asc ou desc)")
    ] = schemas.SortOrder.ASC,
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "O preço mínimo não pode ser maior que o preço máximo.",
        )

    filters = schemas.ProductFilter(
        pagination=schemas.PaginationParams(limit=limit, offset=offset),
        search=search,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    items, total = crud.list_products(db, filters)
    return schemas.Page(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{product_id}",
    response_model=schemas.ProductRead,
    summary="Busca produto pelo ID",
    responses=_NOT_FOUND_RESPONSE,
)
def get_product(product_id: int, db: DbSession):
    return _get_or_404(db, product_id)


@router.patch(
    "/{product_id}",
    response_model=schemas.ProductRead,
    summary="Atualiza parcialmente um produto",
    responses=_NOT_FOUND_RESPONSE,
)
def update_product(product_id: int, data: schemas.ProductUpdate, db: DbSession):
    product = _get_or_404(db, product_id)
    if data.category_id is not None:
        _ensure_category_exists(db, data.category_id)
    try:
        return crud.update_product(db, product, data)
    except IntegrityError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "A categoria informada não existe."
        ) from exc


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove um produto",
    responses=_NOT_FOUND_RESPONSE,
)
def delete_product(product_id: int, db: DbSession):
    crud.delete_product(db, _get_or_404(db, product_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)

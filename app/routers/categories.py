from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/categories", tags=["Categorias"])

DbSession = Annotated[Session, Depends(get_db)]


def _get_or_404(db: Session, category_id: int):
    category = crud.get_category(db, category_id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria não encontrada.")
    return category


@router.post("", response_model=schemas.CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(data: schemas.CategoryCreate, db: DbSession):
    if crud.get_category_by_name(db, data.name):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma categoria com esse nome.")
    return crud.create_category(db, data)


@router.get("", response_model=schemas.Page[schemas.CategoryRead])
def list_categories(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items, total = crud.list_categories(db, limit, offset)
    return schemas.Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{category_id}", response_model=schemas.CategoryRead)
def get_category(category_id: int, db: DbSession):
    return _get_or_404(db, category_id)


@router.patch("/{category_id}", response_model=schemas.CategoryRead)
def update_category(category_id: int, data: schemas.CategoryUpdate, db: DbSession):
    category = _get_or_404(db, category_id)
    if data.name and data.name != category.name and crud.get_category_by_name(db, data.name):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma categoria com esse nome.")
    return crud.update_category(db, category, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: DbSession):
    category = _get_or_404(db, category_id)
    if crud.category_has_products(db, category_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Não é possível excluir uma categoria que possui produtos.",
        )
    crud.delete_category(db, category)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

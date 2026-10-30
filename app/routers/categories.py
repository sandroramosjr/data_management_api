from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db

router = APIRouter(prefix="/categories", tags=["Categorias"])

DbSession = Annotated[Session, Depends(get_db)]

_NOT_FOUND_RESPONSE = {status.HTTP_404_NOT_FOUND: {"model": schemas.ErrorResponse}}
_CONFLICT_RESPONSE = {status.HTTP_409_CONFLICT: {"model": schemas.ErrorResponse}}


def _get_or_404(db: Session, category_id: int) -> models.Category:
    category = crud.get_category(db, category_id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria não encontrada.")
    return category


@router.post(
    "",
    response_model=schemas.CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma nova categoria",
    responses=_CONFLICT_RESPONSE,
)
def create_category(data: schemas.CategoryCreate, response: Response, db: DbSession):
    if crud.get_category_by_name(db, data.name):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma categoria com esse nome.")
    try:
        category = crud.create_category(db, data)
    except IntegrityError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Já existe uma categoria com esse nome."
        ) from exc
    response.headers["Location"] = f"/categories/{category.id}"
    return category


@router.get(
    "",
    response_model=schemas.Page[schemas.CategoryRead],
    summary="Lista categorias com paginação",
)
def list_categories(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100, description="Itens por página")] = 20,
    offset: Annotated[int, Query(ge=0, description="Deslocamento inicial")] = 0,
):
    pagination = schemas.PaginationParams(limit=limit, offset=offset)
    items, total = crud.list_categories(db, pagination)
    return schemas.Page(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/summary",
    response_model=list[schemas.CategorySummary],
    summary="Agrega estoque e valor financeiro por categoria",
)
def list_category_summaries(db: DbSession):
    return crud.list_category_summaries(db)


@router.get(
    "/{category_id}",
    response_model=schemas.CategoryRead,
    summary="Busca categoria pelo ID",
    responses=_NOT_FOUND_RESPONSE,
)
def get_category(category_id: int, db: DbSession):
    return _get_or_404(db, category_id)


@router.patch(
    "/{category_id}",
    response_model=schemas.CategoryRead,
    summary="Atualiza parcialmente uma categoria",
    responses={**_NOT_FOUND_RESPONSE, **_CONFLICT_RESPONSE},
)
def update_category(category_id: int, data: schemas.CategoryUpdate, db: DbSession):
    category = _get_or_404(db, category_id)
    if data.name and data.name != category.name and crud.get_category_by_name(db, data.name):
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma categoria com esse nome.")
    try:
        return crud.update_category(db, category, data)
    except IntegrityError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Já existe uma categoria com esse nome."
        ) from exc


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove uma categoria sem produtos vinculados",
    responses={**_NOT_FOUND_RESPONSE, **_CONFLICT_RESPONSE},
)
def delete_category(category_id: int, db: DbSession):
    category = _get_or_404(db, category_id)
    if crud.category_has_products(db, category_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Não é possível excluir uma categoria que possui produtos.",
        )
    try:
        crud.delete_category(db, category)
    except IntegrityError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Não é possível excluir uma categoria que possui produtos.",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

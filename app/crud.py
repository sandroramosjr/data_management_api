"""Camada de acesso a dados: concentra todas as consultas e transações SQL."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import InstrumentedAttribute, Session, joinedload

from app import models, schemas

_CENT = Decimal("0.01")

_PRODUCT_SORT_COLUMNS: dict[schemas.ProductSortField, InstrumentedAttribute[Any]] = {
    schemas.ProductSortField.ID: models.Product.id,
    schemas.ProductSortField.NAME: models.Product.name,
    schemas.ProductSortField.PRICE: models.Product.price,
    schemas.ProductSortField.STOCK: models.Product.stock,
    schemas.ProductSortField.CREATED_AT: models.Product.created_at,
}


def _commit_or_rollback(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise


def _to_money(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


# ---------- Categorias ----------
def get_category(db: Session, category_id: int) -> models.Category | None:
    return db.get(models.Category, category_id)


def get_category_by_name(db: Session, name: str) -> models.Category | None:
    return db.scalar(select(models.Category).where(models.Category.name == name))


def list_categories(
    db: Session, pagination: schemas.PaginationParams
) -> tuple[list[models.Category], int]:
    total = db.scalar(select(func.count()).select_from(models.Category)) or 0
    items = db.scalars(
        select(models.Category)
        .order_by(models.Category.id)
        .limit(pagination.limit)
        .offset(pagination.offset)
    ).all()
    return list(items), total


def list_category_summaries(db: Session) -> list[schemas.CategorySummary]:
    """Agrega métricas de inventário por categoria em SQL (LEFT JOIN + GROUP BY)."""
    stmt = (
        select(
            models.Category.id,
            models.Category.name,
            func.count(models.Product.id).label("product_count"),
            func.coalesce(func.sum(models.Product.stock), 0).label("total_stock"),
            func.coalesce(
                func.sum(models.Product.price * models.Product.stock), Decimal("0.00")
            ).label("inventory_value"),
            func.avg(models.Product.price).label("average_price"),
        )
        .outerjoin(models.Product, models.Product.category_id == models.Category.id)
        .group_by(models.Category.id, models.Category.name)
        .order_by(models.Category.id)
    )
    return [
        schemas.CategorySummary(
            id=row.id,
            name=row.name,
            product_count=int(row.product_count),
            total_stock=int(row.total_stock),
            inventory_value=_to_money(row.inventory_value),
            average_price=_to_money(row.average_price) if row.average_price is not None else None,
        )
        for row in db.execute(stmt).all()
    ]


def create_category(db: Session, data: schemas.CategoryCreate) -> models.Category:
    category = models.Category(**data.model_dump())
    db.add(category)
    _commit_or_rollback(db)
    db.refresh(category)
    return category


def update_category(
    db: Session, category: models.Category, data: schemas.CategoryUpdate
) -> models.Category:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    _commit_or_rollback(db)
    db.refresh(category)
    return category


def category_has_products(db: Session, category_id: int) -> bool:
    return bool(db.scalar(select(exists().where(models.Product.category_id == category_id))))


def delete_category(db: Session, category: models.Category) -> None:
    db.delete(category)
    _commit_or_rollback(db)


# ---------- Produtos ----------
def get_product(db: Session, product_id: int) -> models.Product | None:
    stmt = (
        select(models.Product)
        .options(joinedload(models.Product.category))
        .where(models.Product.id == product_id)
    )
    return db.scalar(stmt)


def list_products(db: Session, filters: schemas.ProductFilter) -> tuple[list[models.Product], int]:
    conditions = []
    if filters.search:
        conditions.append(models.Product.name.icontains(filters.search, autoescape=True))
    if filters.category_id is not None:
        conditions.append(models.Product.category_id == filters.category_id)
    if filters.min_price is not None:
        conditions.append(models.Product.price >= filters.min_price)
    if filters.max_price is not None:
        conditions.append(models.Product.price <= filters.max_price)
    if filters.in_stock is not None:
        conditions.append(
            models.Product.stock > 0 if filters.in_stock else models.Product.stock == 0
        )

    sort_column = _PRODUCT_SORT_COLUMNS[filters.sort_by]
    primary_order = (
        sort_column.desc() if filters.sort_order == schemas.SortOrder.DESC else sort_column.asc()
    )
    order_clauses = (
        (primary_order,)
        if filters.sort_by == schemas.ProductSortField.ID
        else (primary_order, models.Product.id.asc())
    )

    total = db.scalar(select(func.count()).select_from(models.Product).where(*conditions)) or 0
    items = db.scalars(
        select(models.Product)
        .options(joinedload(models.Product.category))
        .where(*conditions)
        .order_by(*order_clauses)
        .limit(filters.pagination.limit)
        .offset(filters.pagination.offset)
    ).all()
    return list(items), total


def create_product(db: Session, data: schemas.ProductCreate) -> models.Product:
    product = models.Product(**data.model_dump())
    db.add(product)
    _commit_or_rollback(db)
    db.refresh(product)
    db.refresh(product, attribute_names=["category"])
    return product


def update_product(
    db: Session, product: models.Product, data: schemas.ProductUpdate
) -> models.Product:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    _commit_or_rollback(db)
    db.refresh(product)
    db.refresh(product, attribute_names=["category"])
    return product


def delete_product(db: Session, product: models.Product) -> None:
    db.delete(product)
    _commit_or_rollback(db)

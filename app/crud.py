"""Camada de acesso a dados: toda a interação com o banco passa por aqui."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas


# ---------- Categorias ----------
def get_category(db: Session, category_id: int) -> models.Category | None:
    return db.get(models.Category, category_id)


def get_category_by_name(db: Session, name: str) -> models.Category | None:
    return db.scalar(select(models.Category).where(models.Category.name == name))


def list_categories(db: Session, limit: int, offset: int) -> tuple[list[models.Category], int]:
    total = db.scalar(select(func.count()).select_from(models.Category)) or 0
    items = db.scalars(
        select(models.Category).order_by(models.Category.id).limit(limit).offset(offset)
    ).all()
    return list(items), total


def create_category(db: Session, data: schemas.CategoryCreate) -> models.Category:
    category = models.Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session, category: models.Category, data: schemas.CategoryUpdate
) -> models.Category:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def category_has_products(db: Session, category_id: int) -> bool:
    return (
        db.scalar(
            select(func.count()).select_from(models.Product).where(
                models.Product.category_id == category_id
            )
        )
        or 0
    ) > 0


def delete_category(db: Session, category: models.Category) -> None:
    db.delete(category)
    db.commit()


# ---------- Produtos ----------
def get_product(db: Session, product_id: int) -> models.Product | None:
    return db.get(models.Product, product_id)


def list_products(
    db: Session,
    limit: int,
    offset: int,
    *,
    search: str | None = None,
    category_id: int | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
) -> tuple[list[models.Product], int]:
    filters = []
    if search:
        filters.append(models.Product.name.ilike(f"%{search}%"))
    if category_id is not None:
        filters.append(models.Product.category_id == category_id)
    if min_price is not None:
        filters.append(models.Product.price >= min_price)
    if max_price is not None:
        filters.append(models.Product.price <= max_price)

    total = db.scalar(select(func.count()).select_from(models.Product).where(*filters)) or 0
    items = db.scalars(
        select(models.Product)
        .where(*filters)
        .order_by(models.Product.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return list(items), total


def create_product(db: Session, data: schemas.ProductCreate) -> models.Product:
    product = models.Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(
    db: Session, product: models.Product, data: schemas.ProductUpdate
) -> models.Product:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product: models.Product) -> None:
    db.delete(product)
    db.commit()

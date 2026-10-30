from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ---------- Categorias ----------
class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Eletrônicos"])
    description: str | None = Field(default=None, max_length=255)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


# ---------- Produtos ----------
class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=150, examples=["Teclado mecânico"])
    description: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2, examples=["249.90"])
    stock: int = Field(default=0, ge=0)
    category_id: int


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)
    category_id: int | None = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


# ---------- Paginação ----------
class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int

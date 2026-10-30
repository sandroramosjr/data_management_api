from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


# ---------- Ordenação e filtros (estruturas de dados) ----------
class ProductSortField(StrEnum):
    ID = "id"
    NAME = "name"
    PRICE = "price"
    STOCK = "stock"
    CREATED_AT = "created_at"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True, slots=True)
class PaginationParams:
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class ProductFilter:
    pagination: PaginationParams = PaginationParams()
    search: str | None = None
    category_id: int | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    in_stock: bool | None = None
    sort_by: ProductSortField = ProductSortField.ID
    sort_order: SortOrder = SortOrder.ASC


class _NonNullableUpdateMixin(BaseModel):
    """Impede que campos obrigatórios sejam explicitamente enviados como `null` em PATCH."""

    _NON_NULLABLE_FIELDS: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _reject_null_on_required_fields(self) -> Self:
        null_fields = [
            field
            for field in sorted(self.model_fields_set & self._NON_NULLABLE_FIELDS)
            if getattr(self, field) is None
        ]
        if null_fields:
            joined = ", ".join(null_fields)
            raise ValueError(f"Campos obrigatórios não podem ser nulos: {joined}.")
        return self


# ---------- Categorias ----------
class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Eletrônicos"])
    description: str | None = Field(
        default=None, max_length=255, examples=["Periféricos e hardware"]
    )


class CategoryCreate(CategoryBase):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class CategoryUpdate(_NonNullableUpdateMixin):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    _NON_NULLABLE_FIELDS: ClassVar[frozenset[str]] = frozenset({"name"})

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class CategorySummary(BaseModel):
    """Métricas agregadas por categoria calculadas diretamente em SQL."""

    id: int
    name: str
    product_count: int
    total_stock: int
    inventory_value: Decimal
    average_price: Decimal | None


# ---------- Produtos ----------
class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=150, examples=["Teclado mecânico"])
    description: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2, examples=["249.90"])
    stock: int = Field(default=0, ge=0, examples=[10])
    category_id: int = Field(examples=[1])


class ProductCreate(ProductBase):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ProductUpdate(_NonNullableUpdateMixin):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    _NON_NULLABLE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"name", "price", "stock", "category_id"}
    )

    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)
    category_id: int | None = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: CategoryRead
    created_at: datetime
    updated_at: datetime


# ---------- Respostas genéricas e erros ----------
class ErrorResponse(BaseModel):
    detail: str


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int

    @computed_field
    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total

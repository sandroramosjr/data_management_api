"""Garantias de integridade aplicadas pelo próprio banco (sem passar pela API)."""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Category, Product


@pytest.fixture()
def category(db_session):
    category = Category(name="Eletrônicos")
    db_session.add(category)
    db_session.commit()
    return category


def _product(category_id, **overrides):
    values = {"name": "Teclado", "price": Decimal("10.00"), "stock": 1, "category_id": category_id}
    values.update(overrides)
    return Product(**values)


def test_negative_price_is_rejected_by_database(db_session, category):
    db_session.add(_product(category.id, price=Decimal("-1")))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_negative_stock_is_rejected_by_database(db_session, category):
    db_session.add(_product(category.id, stock=-1))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_unknown_category_is_rejected_by_foreign_key(db_session):
    db_session.add(_product(category_id=9999))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_duplicate_category_name_is_rejected_by_unique_index(db_session, category):
    db_session.add(Category(name="Eletrônicos"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_category_with_products_cannot_be_deleted(db_session, category):
    db_session.add(_product(category.id))
    db_session.commit()

    db_session.delete(category)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_price_roundtrips_as_exact_decimal(db_session, category):
    product = _product(category.id, price=Decimal("249.90"))
    db_session.add(product)
    db_session.commit()
    db_session.expire_all()

    assert db_session.get(Product, product.id).price == Decimal("249.90")

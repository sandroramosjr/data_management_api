from unittest.mock import patch

import pytest
from sqlalchemy import event
from sqlalchemy.exc import OperationalError

from app.database import get_db


@pytest.fixture()
def category(client):
    return client.post("/categories", json={"name": "Eletrônicos"}).json()


def _product(category_id, **overrides):
    payload = {"name": "Teclado", "price": "249.90", "stock": 10, "category_id": category_id}
    payload.update(overrides)
    return payload


def test_create_product_returns_location_and_nested_category(client, category):
    response = client.post("/products", json=_product(category["id"], name="  Teclado  "))
    assert response.status_code == 201
    body = response.json()
    assert response.headers["Location"] == f"/products/{body['id']}"
    assert body["name"] == "Teclado"
    assert body["price"] == "249.90"
    assert body["category"] == category
    assert "created_at" in body


def test_create_product_with_unknown_category_returns_422(client):
    response = client.post("/products", json=_product(999))
    assert response.status_code == 422


def test_concurrent_deleted_category_rolls_back_and_returns_422(client, monkeypatch):
    monkeypatch.setattr("app.routers.products._ensure_category_exists", lambda _db, _cid: None)
    response = client.post("/products", json=_product(999))
    assert response.status_code == 422


@pytest.mark.parametrize(
    "overrides",
    [
        {"price": "-1"},
        {"stock": -5},
        {"name": ""},
        {"name": "   "},
        {"price": "10.999"},
        {"campo_inexistente": "valor"},
    ],
)
def test_invalid_payload_returns_422(client, category, overrides):
    response = client.post("/products", json=_product(category["id"], **overrides))
    assert response.status_code == 422


@pytest.mark.parametrize("null_field", ["name", "price", "stock", "category_id"])
def test_update_product_rejects_null_on_required_fields(client, category, null_field):
    product = client.post("/products", json=_product(category["id"])).json()
    response = client.patch(f"/products/{product['id']}", json={null_field: None})
    assert response.status_code == 422


def test_get_missing_product_returns_404(client):
    assert client.get("/products/999").status_code == 404


def test_update_product_partially_and_reassign_category(client, category):
    other = client.post("/categories", json={"name": "Acessórios"}).json()
    product = client.post("/products", json=_product(category["id"], description="Com fio")).json()

    response = client.patch(
        f"/products/{product['id']}",
        json={"stock": 3, "description": None, "category_id": other["id"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stock"] == 3
    assert body["name"] == "Teclado"
    assert body["description"] is None
    assert body["category"] == other


def test_update_product_to_unknown_category_returns_422(client, category):
    product = client.post("/products", json=_product(category["id"])).json()
    response = client.patch(f"/products/{product['id']}", json={"category_id": 999})
    assert response.status_code == 422


def test_delete_product(client, category):
    product = client.post("/products", json=_product(category["id"])).json()
    assert client.delete(f"/products/{product['id']}").status_code == 204
    assert client.get(f"/products/{product['id']}").status_code == 404


def test_list_products_filters_sorting_and_wildcard_escape(client, category):
    other = client.post("/categories", json={"name": "Livros"}).json()
    client.post(
        "/products", json=_product(category["id"], name="Teclado 100%", price="200", stock=5)
    )
    client.post(
        "/products", json=_product(category["id"], name="Mouse 1000dpi", price="50", stock=0)
    )
    client.post("/products", json=_product(other["id"], name="Livro Python", price="80", stock=12))

    assert client.get("/products").json()["total"] == 3
    # '%' literal deve casar apenas "Teclado 100%", sem agir como curinga SQL para "1000dpi".
    assert client.get("/products", params={"search": "100%"}).json()["total"] == 1
    assert client.get("/products", params={"category_id": other["id"]}).json()["total"] == 1
    assert client.get("/products", params={"min_price": 60, "max_price": 100}).json()["total"] == 1
    assert client.get("/products", params={"in_stock": True}).json()["total"] == 2
    assert client.get("/products", params={"in_stock": False}).json()["total"] == 1

    sorted_desc = client.get("/products", params={"sort_by": "price", "sort_order": "desc"}).json()[
        "items"
    ]
    assert [item["price"] for item in sorted_desc] == ["200.00", "80.00", "50.00"]

    invalid_range = client.get("/products", params={"min_price": 200, "max_price": 50})
    assert invalid_range.status_code == 422


def test_list_products_avoids_n_plus_one_queries(client, engine):
    categories = [
        client.post("/categories", json={"name": f"Categoria {i}"}).json() for i in range(5)
    ]
    for idx, cat in enumerate(categories):
        client.post("/products", json=_product(cat["id"], name=f"Produto {idx}"))

    statements: list[str] = []

    def _count_queries(_conn, _cursor, statement, _params, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", _count_queries)
    try:
        response = client.get("/products")
    finally:
        event.remove(engine, "before_cursor_execute", _count_queries)

    assert response.status_code == 200
    assert len(response.json()["items"]) == 5
    # Apenas 2 SELECTs: 1 para COUNT(*) total + 1 com JOIN das categorias (sem N+1).
    assert len(statements) == 2


def test_health_ok_and_503_when_database_fails(client, session_factory):
    assert client.get("/health").json() == {"status": "ok"}

    with patch.object(
        session_factory.class_,
        "execute",
        side_effect=OperationalError("SELECT 1", {}, Exception("connection refused")),
    ):
        response = client.get("/health")
    assert response.status_code == 503


def test_get_db_dependency_closes_session():
    generator = get_db()
    session = next(generator)
    assert session is not None
    with pytest.raises(StopIteration):
        next(generator)

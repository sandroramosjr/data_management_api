import pytest


@pytest.fixture()
def category(client):
    return client.post("/categories", json={"name": "Eletrônicos"}).json()


def _product(category_id, **overrides):
    payload = {"name": "Teclado", "price": "249.90", "stock": 10, "category_id": category_id}
    payload.update(overrides)
    return payload


def test_create_product(client, category):
    response = client.post("/products", json=_product(category["id"]))
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Teclado"
    assert body["price"] == "249.90"
    assert "created_at" in body


def test_create_product_with_unknown_category_returns_422(client):
    response = client.post("/products", json=_product(999))
    assert response.status_code == 422


@pytest.mark.parametrize(
    "overrides",
    [{"price": "-1"}, {"stock": -5}, {"name": ""}, {"price": "10.999"}],
)
def test_invalid_payload_returns_422(client, category, overrides):
    response = client.post("/products", json=_product(category["id"], **overrides))
    assert response.status_code == 422


def test_get_missing_product_returns_404(client):
    assert client.get("/products/999").status_code == 404


def test_update_product_partially(client, category):
    product = client.post("/products", json=_product(category["id"])).json()
    response = client.patch(f"/products/{product['id']}", json={"stock": 3})
    assert response.status_code == 200
    assert response.json()["stock"] == 3
    assert response.json()["name"] == "Teclado"


def test_update_product_to_unknown_category_returns_422(client, category):
    product = client.post("/products", json=_product(category["id"])).json()
    response = client.patch(f"/products/{product['id']}", json={"category_id": 999})
    assert response.status_code == 422


def test_delete_product(client, category):
    product = client.post("/products", json=_product(category["id"])).json()
    assert client.delete(f"/products/{product['id']}").status_code == 204
    assert client.get(f"/products/{product['id']}").status_code == 404


def test_list_products_with_filters(client, category):
    other = client.post("/categories", json={"name": "Livros"}).json()
    client.post("/products", json=_product(category["id"], name="Teclado", price="200"))
    client.post("/products", json=_product(category["id"], name="Mouse", price="50"))
    client.post("/products", json=_product(other["id"], name="Livro Python", price="80"))

    assert client.get("/products").json()["total"] == 3
    assert client.get("/products", params={"search": "mou"}).json()["total"] == 1
    assert client.get("/products", params={"category_id": other["id"]}).json()["total"] == 1
    assert client.get("/products", params={"min_price": 60, "max_price": 100}).json()["total"] == 1


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}

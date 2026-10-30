def _make_category(client, name="Eletrônicos"):
    return client.post("/categories", json={"name": name}).json()


def test_create_and_get_category(client):
    response = client.post("/categories", json={"name": "Livros", "description": "Impressos"})
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Livros"

    fetched = client.get(f"/categories/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == created


def test_duplicate_category_name_returns_409(client):
    _make_category(client, "Livros")
    response = client.post("/categories", json={"name": "Livros"})
    assert response.status_code == 409


def test_empty_name_returns_422(client):
    assert client.post("/categories", json={"name": ""}).status_code == 422


def test_get_missing_category_returns_404(client):
    assert client.get("/categories/999").status_code == 404


def test_update_category_partially(client):
    category = _make_category(client)
    response = client.patch(f"/categories/{category['id']}", json={"description": "Novo"})
    assert response.status_code == 200
    assert response.json()["name"] == "Eletrônicos"
    assert response.json()["description"] == "Novo"


def test_list_categories_pagination(client):
    for i in range(5):
        _make_category(client, f"Cat {i}")
    page = client.get("/categories", params={"limit": 2, "offset": 2}).json()
    assert page["total"] == 5
    assert len(page["items"]) == 2
    assert page["offset"] == 2


def test_delete_category(client):
    category = _make_category(client)
    assert client.delete(f"/categories/{category['id']}").status_code == 204
    assert client.get(f"/categories/{category['id']}").status_code == 404


def test_cannot_delete_category_with_products(client):
    category = _make_category(client)
    client.post(
        "/products",
        json={"name": "Mouse", "price": "50.00", "category_id": category["id"]},
    )
    assert client.delete(f"/categories/{category['id']}").status_code == 409

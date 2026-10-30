def _make_category(client, name="Eletrônicos", description=None):
    return client.post("/categories", json={"name": name, "description": description}).json()


def test_create_and_get_category(client):
    response = client.post("/categories", json={"name": "  Livros  ", "description": "Impressos"})
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Livros"
    assert response.headers["Location"] == f"/categories/{created['id']}"

    fetched = client.get(f"/categories/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == created


def test_duplicate_category_name_returns_409(client):
    _make_category(client, "Livros")
    response = client.post("/categories", json={"name": "Livros"})
    assert response.status_code == 409


def test_concurrent_duplicate_category_rolls_back_and_returns_409(client, monkeypatch):
    _make_category(client, "Livros")
    monkeypatch.setattr("app.crud.get_category_by_name", lambda _db, _name: None)
    response = client.post("/categories", json={"name": "Livros"})
    assert response.status_code == 409


def test_empty_or_whitespace_name_returns_422(client):
    assert client.post("/categories", json={"name": ""}).status_code == 422
    assert client.post("/categories", json={"name": "   "}).status_code == 422


def test_unknown_field_in_category_payload_returns_422(client):
    assert client.post("/categories", json={"name": "Livros", "extra": 1}).status_code == 422


def test_get_missing_category_returns_404(client):
    assert client.get("/categories/999").status_code == 404


def test_update_category_partially_and_clear_description(client):
    category = _make_category(client, description="Inicial")
    updated = client.patch(f"/categories/{category['id']}", json={"description": "Novo"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Eletrônicos"
    assert updated.json()["description"] == "Novo"

    cleared = client.patch(f"/categories/{category['id']}", json={"description": None})
    assert cleared.status_code == 200
    assert cleared.json()["description"] is None


def test_update_category_rejects_null_name_and_duplicate_name(client):
    first = _make_category(client, "Eletrônicos")
    second = _make_category(client, "Livros")

    assert client.patch(f"/categories/{second['id']}", json={"name": None}).status_code == 422
    assert (
        client.patch(f"/categories/{second['id']}", json={"name": first["name"]}).status_code == 409
    )


def test_list_categories_pagination_and_has_more(client):
    for i in range(5):
        _make_category(client, f"Cat {i}")

    first_page = client.get("/categories", params={"limit": 2, "offset": 2}).json()
    assert first_page["total"] == 5
    assert len(first_page["items"]) == 2
    assert first_page["offset"] == 2
    assert first_page["has_more"] is True

    last_page = client.get("/categories", params={"limit": 2, "offset": 4}).json()
    assert len(last_page["items"]) == 1
    assert last_page["has_more"] is False


def test_category_summaries_aggregate_inventory_with_left_join(client):
    tech = _make_category(client, "Eletrônicos")
    empty = _make_category(client, "Papelaria")

    client.post(
        "/products",
        json={"name": "Teclado", "price": "200.00", "stock": 3, "category_id": tech["id"]},
    )
    client.post(
        "/products",
        json={"name": "Mouse", "price": "100.00", "stock": 2, "category_id": tech["id"]},
    )

    response = client.get("/categories/summary")
    assert response.status_code == 200
    by_id = {item["id"]: item for item in response.json()}

    assert by_id[tech["id"]] == {
        "id": tech["id"],
        "name": "Eletrônicos",
        "product_count": 2,
        "total_stock": 5,
        "inventory_value": "800.00",
        "average_price": "150.00",
    }
    assert by_id[empty["id"]] == {
        "id": empty["id"],
        "name": "Papelaria",
        "product_count": 0,
        "total_stock": 0,
        "inventory_value": "0.00",
        "average_price": None,
    }


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

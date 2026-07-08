from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_user_id, repository
from app.main import app


def test_categories_endpoint_returns_default_active_categories() -> None:
    client = TestClient(app)

    response = client.get("/categories")

    assert response.status_code == 200
    categories = response.json()
    names = [category["name"] for category in categories]
    assert "Alimentação" in names
    assert "Supermercado" in names
    assert "Outros" in names
    assert all(category["status"] == "active" for category in categories)
    assert all(category["is_system"] for category in categories if category["user_id"] is None)


def test_default_categories_are_expenses_except_outros() -> None:
    client = TestClient(app)

    response = client.get("/categories")

    assert response.status_code == 200
    categories_by_name = {category["name"]: category for category in response.json()}
    for name, category in categories_by_name.items():
        if category["user_id"] is None and name != "Outros":
            assert category["type"] == "expense"
    assert categories_by_name["Outros"]["type"] == "both"


def test_create_update_and_soft_delete_category() -> None:
    client = TestClient(app)
    category_name = f"Categoria {uuid4()}"

    create_response = client.post(
        "/categories",
        json={"name": category_name, "type": "expense", "status": "active"},
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["name"] == category_name
    assert created["type"] == "expense"
    assert created["status"] == "active"
    assert created["user_id"] == get_user_id()

    update_response = client.put(
        f"/categories/{created['id']}",
        json={"name": f"{category_name} editada", "type": "income"},
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == f"{category_name} editada"
    assert updated["type"] == "income"

    delete_response = client.delete(f"/categories/{created['id']}")

    assert delete_response.status_code == 200
    deleted = delete_response.json()
    assert deleted["status"] == "inactive"

    list_response = client.get("/categories")
    assert list_response.status_code == 200
    ids = {category["id"] for category in list_response.json()}
    assert created["id"] not in ids


def test_create_category_rejects_duplicate_active_name() -> None:
    client = TestClient(app)
    category_name = f"Categoria duplicada {uuid4()}"

    first = client.post("/categories", json={"name": category_name, "type": "expense", "status": "active"})
    duplicate = client.post("/categories", json={"name": f"  {category_name.upper()}  ", "type": "income", "status": "active"})

    assert first.status_code == 200
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "category_already_exists"
    assert duplicate.json()["error"]["message"] == "Essa categoria já existe."
    matches = [category for category in repository._all_categories(get_user_id()) if category["name"].strip().casefold() == category_name.casefold()]
    assert len(matches) == 1


def test_create_category_reactivates_inactive_name_without_duplicate() -> None:
    client = TestClient(app)
    category_name = f"Categoria reativada {uuid4()}"

    create_response = client.post("/categories", json={"name": category_name, "type": "expense", "status": "active"})
    created = create_response.json()
    delete_response = client.delete(f"/categories/{created['id']}")
    reactivate_response = client.post("/categories", json={"name": f" {category_name} ", "type": "income", "status": "active"})

    assert create_response.status_code == 200
    assert delete_response.status_code == 200
    assert reactivate_response.status_code == 200
    assert reactivate_response.headers["X-Financy-Category-Action"] == "reactivated"
    reactivated = reactivate_response.json()
    assert reactivated["id"] == created["id"]
    assert reactivated["status"] == "active"
    assert reactivated["type"] == "income"
    matches = [category for category in repository._all_categories(get_user_id()) if category["name"].strip().casefold() == category_name.casefold()]
    assert len(matches) == 1


def test_system_category_cannot_be_updated_or_deleted() -> None:
    client = TestClient(app)
    categories = client.get("/categories").json()
    system_category = next(category for category in categories if category["is_system"])

    update_response = client.put(f"/categories/{system_category['id']}", json={"type": "income"})
    delete_response = client.delete(f"/categories/{system_category['id']}")

    assert update_response.status_code == 400
    assert update_response.json()["error"]["code"] == "category_system_protected"
    assert delete_response.status_code == 400
    assert delete_response.json()["error"]["code"] == "category_system_protected"


def test_categories_list_treats_legacy_without_status_as_active() -> None:
    category_name = f"Categoria legada {uuid4()}"
    repository.create_category(get_user_id(), {"name": category_name, "type": "both"})
    client = TestClient(app)

    response = client.get("/categories")

    assert response.status_code == 200
    names = [category["name"] for category in response.json()]
    assert category_name in names


def test_category_invalid_type_is_rejected() -> None:
    client = TestClient(app)

    response = client.post("/categories", json={"name": "Categoria inválida", "type": "invalid"})

    assert response.status_code == 422


def test_category_missing_name_is_rejected() -> None:
    client = TestClient(app)

    missing_response = client.post("/categories", json={"type": "expense"})
    blank_response = client.post("/categories", json={"name": "   ", "type": "expense"})

    assert missing_response.status_code == 422
    assert blank_response.status_code == 422


def test_category_update_requires_user_ownership() -> None:
    client = TestClient(app)
    other_category = repository.create_category(
        "00000000-0000-4000-8000-000000000999",
        {"name": f"Categoria de outro usuário {uuid4()}", "type": "expense", "status": "active"},
    )

    response = client.put(f"/categories/{other_category['id']}", json={"name": "Nao deve atualizar"})

    assert response.status_code == 404

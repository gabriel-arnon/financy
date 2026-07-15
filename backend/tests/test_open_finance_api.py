from fastapi.testclient import TestClient

from app.api.deps import get_open_finance_service
from app.api.deps import repository
from app.core.config import settings
from app.main import app


def test_open_finance_status_is_disabled_when_feature_off(monkeypatch) -> None:
    monkeypatch.setattr(settings, "open_finance_enabled", False)
    monkeypatch.setattr(settings, "open_finance_owner_user_id", settings.dev_user_id)

    response = TestClient(app).get("/open-finance/status")

    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_open_finance_items_requires_owner(monkeypatch) -> None:
    monkeypatch.setattr(settings, "open_finance_enabled", True)
    monkeypatch.setattr(settings, "open_finance_owner_user_id", "00000000-0000-4000-8000-000000009999")

    response = TestClient(app).get("/open-finance/items")

    assert response.status_code == 404


def test_open_finance_items_lists_for_owner(monkeypatch) -> None:
    monkeypatch.setattr(settings, "open_finance_enabled", True)
    monkeypatch.setattr(settings, "open_finance_owner_user_id", settings.dev_user_id)
    repository.upsert_open_finance_item(
        settings.dev_user_id,
        {
            "provider": "pluggy",
            "external_item_id": "api-item",
            "connector_name": "Meu Pluggy",
            "institution_name": "Banco Teste",
            "status": "active",
            "metadata": {},
        },
    )

    response = TestClient(app).get("/open-finance/items")

    assert response.status_code == 200
    assert "api-item" in {item["external_item_id"] for item in response.json()}


def test_open_finance_webhook_rejects_invalid_secret(monkeypatch) -> None:
    monkeypatch.setattr(settings, "open_finance_enabled", True)
    monkeypatch.setattr(settings, "pluggy_webhook_secret", "expected-secret")

    response = TestClient(app).post("/open-finance/webhook/pluggy", headers={"X-Pluggy-Signature": "bad-secret"}, json={})

    assert response.status_code == 401


def test_open_finance_webhook_accepts_valid_secret(monkeypatch) -> None:
    monkeypatch.setattr(settings, "open_finance_enabled", True)
    monkeypatch.setattr(settings, "pluggy_webhook_secret", "expected-secret")
    monkeypatch.setattr(settings, "open_finance_owner_user_id", settings.dev_user_id)
    monkeypatch.setattr(settings, "pluggy_client_id", None)
    monkeypatch.setattr(settings, "pluggy_client_secret", None)

    response = TestClient(app).post("/open-finance/webhook/pluggy", headers={"X-Pluggy-Signature": "expected-secret"}, json={})

    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}


def test_open_finance_webhook_dispatches_item_sync(monkeypatch) -> None:
    class FakeOpenFinanceService:
        def __init__(self) -> None:
            self.synced_items = []

        def sync_item(self, user_id: str, external_item_id: str):
            self.synced_items.append((user_id, external_item_id))
            return {"run": {"status": "success"}, "items": []}

    fake_service = FakeOpenFinanceService()
    monkeypatch.setattr(settings, "open_finance_enabled", True)
    monkeypatch.setattr(settings, "pluggy_webhook_secret", "expected-secret")
    monkeypatch.setattr(settings, "open_finance_owner_user_id", settings.dev_user_id)
    monkeypatch.setattr(settings, "pluggy_client_id", "client")
    monkeypatch.setattr(settings, "pluggy_client_secret", "secret")
    app.dependency_overrides[get_open_finance_service] = lambda: fake_service
    try:
        response = TestClient(app).post(
            "/open-finance/webhook/pluggy",
            headers={"X-Pluggy-Signature": "expected-secret"},
            json={"itemId": "item-webhook"},
        )
    finally:
        app.dependency_overrides.pop(get_open_finance_service, None)

    assert response.status_code == 200
    assert response.json() == {"status": "synced"}
    assert fake_service.synced_items == [(settings.dev_user_id, "item-webhook")]

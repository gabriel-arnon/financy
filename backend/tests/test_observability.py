from fastapi.testclient import TestClient

from app.main import app


def test_request_id_header_is_generated() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.headers["X-Request-Id"]
    assert response.headers["X-Process-Time-Ms"]


def test_request_id_header_is_propagated() -> None:
    response = TestClient(app).get("/health", headers={"X-Request-Id": "test-request-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "test-request-123"


def test_app_error_includes_request_id() -> None:
    response = TestClient(app).post(
        "/transactions",
        headers={"X-Request-Id": "missing-origin-request"},
        json={
            "transaction_date": "2026-06-10",
            "description": "TRANSACAO SEM ORIGEM",
            "amount": "10.00",
            "type": "expense",
            "status": "confirmed",
        },
    )

    assert response.status_code == 400
    assert response.headers["X-Request-Id"] == "missing-origin-request"
    assert response.json()["error"]["request_id"] == "missing-origin-request"

import base64
import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


USER_A = "00000000-0000-4000-8000-0000000000a1"
USER_B = "00000000-0000-4000-8000-0000000000b2"


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def make_token(user_id: str, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "aud": "authenticated",
        "exp": int(time.time()) + 300,
    }
    encoded_header = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64url(signature)}"


def auth_headers(user_id: str, secret: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(user_id, secret)}"}


def test_financial_endpoint_requires_token_when_auth_required(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_required", True)
    monkeypatch.setattr(settings, "auth_dev_bypass", False)
    client = TestClient(app)

    response = client.get("/transactions")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


def test_health_remains_public_when_auth_required(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_required", True)
    monkeypatch.setattr(settings, "auth_dev_bypass", False)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_users_do_not_see_or_access_each_others_accounts(monkeypatch) -> None:
    secret = "endpoint-test-secret"
    monkeypatch.setattr(settings, "jwt_secret", secret)
    monkeypatch.setattr(settings, "auth_required", True)
    monkeypatch.setattr(settings, "auth_dev_bypass", False)
    monkeypatch.setattr(settings, "supabase_audience", "authenticated")
    monkeypatch.setattr(settings, "supabase_jwt_issuer", None)
    client = TestClient(app)

    account_a = client.post(
        "/accounts",
        headers=auth_headers(USER_A, secret),
        json={
            "name": "Conta Usuario A",
            "institution": "Banco A",
            "type": "checking",
            "balance": "10.00",
            "status": "active",
        },
    )
    assert account_a.status_code == 200

    account_b = client.post(
        "/accounts",
        headers=auth_headers(USER_B, secret),
        json={
            "name": "Conta Usuario B",
            "institution": "Banco B",
            "type": "checking",
            "balance": "20.00",
            "status": "active",
        },
    )
    assert account_b.status_code == 200

    listed_a = client.get("/accounts", headers=auth_headers(USER_A, secret))
    assert listed_a.status_code == 200
    listed_a_ids = {item["id"] for item in listed_a.json()}

    assert account_a.json()["id"] in listed_a_ids
    assert account_b.json()["id"] not in listed_a_ids

    cross_user_summary = client.get(
        f"/accounts/{account_a.json()['id']}/summary",
        headers=auth_headers(USER_B, secret),
    )
    assert cross_user_summary.status_code == 404


def test_user_cannot_reference_another_users_account_in_transaction(monkeypatch) -> None:
    secret = "transaction-isolation-secret"
    monkeypatch.setattr(settings, "jwt_secret", secret)
    monkeypatch.setattr(settings, "auth_required", True)
    monkeypatch.setattr(settings, "auth_dev_bypass", False)
    monkeypatch.setattr(settings, "supabase_audience", "authenticated")
    client = TestClient(app)

    account_a = client.post(
        "/accounts",
        headers=auth_headers(USER_A, secret),
        json={
            "name": "Conta Referencia A",
            "institution": "Banco A",
            "type": "checking",
            "balance": "0.00",
            "status": "active",
        },
    ).json()

    response = client.post(
        "/transactions",
        headers=auth_headers(USER_B, secret),
        json={
            "account_id": account_a["id"],
            "transaction_date": "2026-07-03",
            "description": "Tentativa cross-user",
            "amount": "1.00",
            "type": "expense",
            "status": "confirmed",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "transaction_account_not_found"

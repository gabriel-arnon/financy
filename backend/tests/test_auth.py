import base64
import hashlib
import hmac
import json
import time

import pytest
from starlette.datastructures import Headers

from app.core.auth import decode_supabase_jwt, get_current_user
from app.core.config import settings
from app.core.errors import AppError


class DummyRequest:
    def __init__(self, authorization: str | None = None) -> None:
        self.headers = Headers({"authorization": authorization} if authorization else {})


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def make_token(payload: dict, secret: str | None = None) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new((secret or settings.jwt_secret).encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64url(signature)}"


def test_valid_supabase_jwt_resolves_current_user(monkeypatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret", "test-secret")
    monkeypatch.setattr(settings, "supabase_jwt_issuer", "https://financy.supabase.co/auth/v1")
    monkeypatch.setattr(settings, "supabase_audience", "authenticated")

    token = make_token(
        {
            "sub": "00000000-0000-4000-8000-000000000123",
            "email": "user@example.com",
            "iss": "https://financy.supabase.co/auth/v1",
            "aud": "authenticated",
            "exp": int(time.time()) + 300,
            "user_metadata": {"full_name": "User Example"},
        },
        secret="test-secret",
    )

    user = decode_supabase_jwt(token)

    assert user.id == "00000000-0000-4000-8000-000000000123"
    assert user.email == "user@example.com"
    assert user.full_name == "User Example"
    assert user.auth_source == "supabase"


def test_invalid_supabase_jwt_signature_fails(monkeypatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret", "correct-secret")
    token = make_token({"sub": "user-id", "exp": int(time.time()) + 300}, secret="wrong-secret")

    with pytest.raises(AppError) as exc:
        decode_supabase_jwt(token)

    assert exc.value.status_code == 401
    assert exc.value.code == "unauthenticated"


def test_missing_token_uses_dev_bypass_only_when_allowed(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_dev_bypass", True)
    monkeypatch.setattr(settings, "environment", "local")

    user = get_current_user(DummyRequest())

    assert user.id == settings.dev_user_id
    assert user.auth_source == "dev_bypass"


def test_missing_token_without_bypass_fails(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_dev_bypass", False)
    monkeypatch.setattr(settings, "auth_required", True)
    monkeypatch.setattr(settings, "environment", "local")

    with pytest.raises(AppError) as exc:
        get_current_user(DummyRequest())

    assert exc.value.status_code == 401


def test_dev_bypass_is_blocked_in_production(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_dev_bypass", True)
    monkeypatch.setattr(settings, "auth_required", True)
    monkeypatch.setattr(settings, "environment", "production")

    with pytest.raises(AppError) as exc:
        get_current_user(DummyRequest())

    assert exc.value.status_code == 401

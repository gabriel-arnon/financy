from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import Request
from pydantic import BaseModel

from app.core.config import settings
from app.core.errors import AppError


class CurrentUser(BaseModel):
    id: str
    email: str | None = None
    full_name: str | None = None
    auth_source: str = "supabase"


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _json_decode(value: str) -> dict[str, Any]:
    return json.loads(_b64url_decode(value).decode("utf-8"))


def _unauthorized(message: str = "Autenticacao obrigatoria.") -> AppError:
    return AppError(message, status_code=401, code="unauthenticated")


def _bearer_token(request: Request | None) -> str | None:
    if request is None:
        return None
    header = request.headers.get("authorization")
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized("Header Authorization invalido.")
    return token.strip()


def _validate_expected_claims(payload: dict[str, Any]) -> None:
    now = int(time.time())
    expires_at = payload.get("exp")
    if expires_at is None or int(expires_at) < now:
        raise _unauthorized("Token expirado.")

    not_before = payload.get("nbf")
    if not_before is not None and int(not_before) > now:
        raise _unauthorized("Token ainda nao valido.")

    issuer = settings.supabase_jwt_issuer
    if issuer and payload.get("iss") != issuer:
        raise _unauthorized("Issuer do token invalido.")

    audience = settings.supabase_audience
    if audience:
        token_audience = payload.get("aud")
        if isinstance(token_audience, list):
            valid_audience = audience in token_audience
        else:
            valid_audience = token_audience == audience
        if not valid_audience:
            raise _unauthorized("Audience do token invalida.")

    if not payload.get("sub"):
        raise _unauthorized("Token sem usuario.")


def decode_supabase_jwt(token: str) -> CurrentUser:
    parts = token.split(".")
    if len(parts) != 3:
        raise _unauthorized("Token invalido.")

    header = _json_decode(parts[0])
    payload = _json_decode(parts[1])
    signature = _b64url_decode(parts[2])

    if header.get("alg") != "HS256":
        raise _unauthorized("Algoritmo de token nao suportado.")

    signing_input = f"{parts[0]}.{parts[1]}".encode("utf-8")
    expected_signature = hmac.new(settings.jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected_signature):
        raise _unauthorized("Assinatura do token invalida.")

    _validate_expected_claims(payload)

    metadata = payload.get("user_metadata") if isinstance(payload.get("user_metadata"), dict) else {}
    return CurrentUser(
        id=str(payload["sub"]),
        email=payload.get("email"),
        full_name=metadata.get("full_name") or metadata.get("name"),
        auth_source="supabase",
    )


def dev_current_user() -> CurrentUser:
    return CurrentUser(id=settings.dev_user_id, auth_source="dev_bypass")


def get_current_user(request: Request | None = None) -> CurrentUser:
    token = _bearer_token(request)
    if token:
        return decode_supabase_jwt(token)

    if settings.allows_dev_auth_bypass:
        return dev_current_user()

    if settings.auth_required:
        raise _unauthorized()

    raise _unauthorized("Autenticacao nao configurada.")

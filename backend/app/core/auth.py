from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.request
from typing import Any

from fastapi import Request
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ec, rsa, padding, utils
from cryptography.hazmat.primitives import hashes
from pydantic import BaseModel

from app.core.config import settings
from app.core.errors import AppError


class CurrentUser(BaseModel):
    id: str
    email: str | None = None
    full_name: str | None = None
    auth_source: str = "supabase"


_JWKS_CACHE: dict[str, Any] | None = None
_JWKS_CACHE_EXPIRES_AT = 0


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _json_decode(value: str) -> dict[str, Any]:
    return json.loads(_b64url_decode(value).decode("utf-8"))


def _unauthorized(message: str = "Autenticacao obrigatoria.") -> AppError:
    return AppError(message, status_code=401, code="unauthenticated")


def _b64url_uint(value: str) -> int:
    return int.from_bytes(_b64url_decode(value), byteorder="big")


def _load_jwks() -> dict[str, Any]:
    global _JWKS_CACHE, _JWKS_CACHE_EXPIRES_AT
    now = int(time.time())
    if _JWKS_CACHE and _JWKS_CACHE_EXPIRES_AT > now:
        return _JWKS_CACHE
    if not settings.supabase_jwks_url:
        raise _unauthorized("JWKS nao configurado.")
    with urllib.request.urlopen(settings.supabase_jwks_url, timeout=5) as response:
        _JWKS_CACHE = json.loads(response.read().decode("utf-8"))
        _JWKS_CACHE_EXPIRES_AT = now + 60 * 10
        return _JWKS_CACHE


def _find_jwk(kid: str | None) -> dict[str, Any]:
    keys = _load_jwks().get("keys", [])
    if kid:
        for key in keys:
            if key.get("kid") == kid:
                return key
    if len(keys) == 1:
        return keys[0]
    raise _unauthorized("Chave publica do token nao encontrada.")


def _verify_jwks_signature(header: dict[str, Any], signing_input: bytes, signature: bytes) -> None:
    alg = header.get("alg")
    key = _find_jwk(header.get("kid"))
    try:
        if alg == "RS256":
            public_key = rsa.RSAPublicNumbers(e=_b64url_uint(key["e"]), n=_b64url_uint(key["n"])).public_key()
            public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
            return
        if alg == "ES256":
            public_key = ec.EllipticCurvePublicNumbers(
                x=_b64url_uint(key["x"]),
                y=_b64url_uint(key["y"]),
                curve=ec.SECP256R1(),
            ).public_key()
            if len(signature) != 64:
                raise InvalidSignature
            der_signature = utils.encode_dss_signature(
                int.from_bytes(signature[:32], byteorder="big"),
                int.from_bytes(signature[32:], byteorder="big"),
            )
            public_key.verify(der_signature, signing_input, ec.ECDSA(hashes.SHA256()))
            return
    except (InvalidSignature, KeyError, ValueError):
        raise _unauthorized("Assinatura do token invalida.")
    raise _unauthorized("Algoritmo de token nao suportado.")


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

    signing_input = f"{parts[0]}.{parts[1]}".encode("utf-8")
    if header.get("alg") == "HS256":
        expected_signature = hmac.new(settings.jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected_signature):
            raise _unauthorized("Assinatura do token invalida.")
    else:
        _verify_jwks_signature(header, signing_input, signature)

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


def _store_request_user(request: Request | None, user: CurrentUser) -> None:
    if request is not None and hasattr(request, "state"):
        request.state.current_user_id = user.id


def get_current_user(request: Request | None = None) -> CurrentUser:
    token = _bearer_token(request)
    if token:
        user = decode_supabase_jwt(token)
        _store_request_user(request, user)
        return user

    if settings.allows_dev_auth_bypass:
        user = dev_current_user()
        _store_request_user(request, user)
        return user

    if settings.auth_required:
        raise _unauthorized()

    raise _unauthorized("Autenticacao nao configurada.")

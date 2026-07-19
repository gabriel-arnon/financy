from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request, Response


REQUEST_ID_HEADER = "X-Request-Id"
PROCESS_TIME_HEADER = "X-Process-Time-Ms"

logger = logging.getLogger("financy.requests")


def _request_id_from_header(value: str | None) -> str:
    if not value:
        return str(uuid4())
    cleaned = value.strip()[:80]
    if not cleaned:
        return str(uuid4())
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:")
    if any(ch not in allowed for ch in cleaned):
        return str(uuid4())
    return cleaned


def _masked_user_id(request: Request) -> str | None:
    user_id = getattr(request.state, "current_user_id", None)
    if not user_id:
        return None
    text = str(user_id)
    if len(text) <= 12:
        return "***"
    return f"{text[:8]}...{text[-4:]}"


def register_observability_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_observability(request: Request, call_next) -> Response:
        request_id = _request_id_from_header(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            response = locals().get("response")
            if response is not None:
                response.headers[REQUEST_ID_HEADER] = request_id
                response.headers[PROCESS_TIME_HEADER] = str(duration_ms)
            logger.info(
                "api_request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "user_id": _masked_user_id(request),
                },
            )

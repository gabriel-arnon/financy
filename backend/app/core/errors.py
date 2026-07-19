import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "app_error") -> None:
        self.message = message
        self.status_code = status_code
        self.code = code


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "request_id": _request_id(request)}},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected_app_error", extra={"request_id": _request_id(request)})
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "Erro interno ao processar a solicitacao.",
                    "request_id": _request_id(request),
                }
            },
        )

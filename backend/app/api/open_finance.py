from typing import Any

from fastapi import APIRouter, Depends, Header, Query

from app.api.deps import get_open_finance_service, get_request_user
from app.core.auth import CurrentUser
from app.core.config import settings
from app.core.errors import AppError
from app.schemas.open_finance import (
    OpenFinanceConnectTokenRead,
    OpenFinanceItemCreate,
    OpenFinanceItemRead,
    OpenFinanceStatus,
    OpenFinanceSyncResponse,
    OpenFinanceSyncRunRead,
    OpenFinanceWebhookResponse,
)
from app.services.open_finance_service import OpenFinanceService


router = APIRouter(prefix="/open-finance", tags=["open-finance"])


def require_open_finance_owner(user: CurrentUser = Depends(get_request_user)) -> str:
    service = get_open_finance_service()
    service.ensure_owner(user.id)
    return user.id


@router.get("/status", response_model=OpenFinanceStatus)
def get_open_finance_status(
    user: CurrentUser = Depends(get_request_user),
    service: OpenFinanceService = Depends(get_open_finance_service),
) -> OpenFinanceStatus:
    if settings.open_finance_enabled and settings.open_finance_owner_user_id and user.id != settings.open_finance_owner_user_id:
        return OpenFinanceStatus(enabled=False, configured=False)
    return OpenFinanceStatus(**service.status())


@router.get("/items", response_model=list[OpenFinanceItemRead])
def list_open_finance_items(
    user_id: str = Depends(require_open_finance_owner),
    service: OpenFinanceService = Depends(get_open_finance_service),
) -> list[OpenFinanceItemRead]:
    return [OpenFinanceItemRead(**item) for item in service.list_items(user_id)]


@router.post("/items", response_model=OpenFinanceItemRead)
def create_open_finance_item(
    payload: OpenFinanceItemCreate,
    user_id: str = Depends(require_open_finance_owner),
    service: OpenFinanceService = Depends(get_open_finance_service),
) -> OpenFinanceItemRead:
    return OpenFinanceItemRead(**service.register_item(user_id, payload.external_item_id))


@router.post("/items/{external_item_id}/sync", response_model=OpenFinanceSyncResponse)
def sync_open_finance_item(
    external_item_id: str,
    user_id: str = Depends(require_open_finance_owner),
    service: OpenFinanceService = Depends(get_open_finance_service),
) -> OpenFinanceSyncResponse:
    return OpenFinanceSyncResponse(**service.sync_item(user_id, external_item_id))


@router.post("/sync", response_model=OpenFinanceSyncResponse)
def sync_open_finance(
    user_id: str = Depends(require_open_finance_owner),
    service: OpenFinanceService = Depends(get_open_finance_service),
) -> OpenFinanceSyncResponse:
    return OpenFinanceSyncResponse(**service.sync_all(user_id))


@router.get("/sync-runs", response_model=list[OpenFinanceSyncRunRead])
def list_open_finance_sync_runs(
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(require_open_finance_owner),
    service: OpenFinanceService = Depends(get_open_finance_service),
) -> list[OpenFinanceSyncRunRead]:
    return [OpenFinanceSyncRunRead(**item) for item in service.list_sync_runs(user_id, limit=limit)]


@router.post("/connect-token", response_model=OpenFinanceConnectTokenRead)
def create_open_finance_connect_token(
    user_id: str = Depends(require_open_finance_owner),
    service: OpenFinanceService = Depends(get_open_finance_service),
) -> OpenFinanceConnectTokenRead:
    return OpenFinanceConnectTokenRead(**service.create_connect_token(user_id))


@router.post("/webhook/pluggy", response_model=OpenFinanceWebhookResponse)
def pluggy_webhook(
    payload: dict[str, Any] | None = None,
    x_pluggy_signature: str | None = Header(default=None),
    service: OpenFinanceService = Depends(get_open_finance_service),
) -> OpenFinanceWebhookResponse:
    if not settings.open_finance_enabled:
        raise AppError("Open Finance nao esta habilitado.", status_code=404, code="open_finance_disabled")
    if not settings.pluggy_webhook_secret:
        raise AppError("Webhook Open Finance nao configurado.", status_code=400, code="open_finance_webhook_not_configured")
    if x_pluggy_signature != settings.pluggy_webhook_secret:
        raise AppError("Webhook Open Finance invalido.", status_code=401, code="open_finance_webhook_invalid")
    body = payload or {}
    item_payload = body.get("item") if isinstance(body.get("item"), dict) else {}
    item_id = body.get("itemId") or body.get("item_id") or item_payload.get("id")
    if item_id and settings.open_finance_owner_user_id and settings.open_finance_configured:
        service.sync_item(settings.open_finance_owner_user_id, str(item_id))
        return OpenFinanceWebhookResponse(status="synced")
    return OpenFinanceWebhookResponse(status="accepted")

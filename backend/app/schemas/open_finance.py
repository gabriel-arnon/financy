from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OpenFinanceStatus(BaseModel):
    enabled: bool
    owner_only: bool = True
    configured: bool
    provider: str = "pluggy"


class OpenFinanceItemCreate(BaseModel):
    external_item_id: str = Field(min_length=1)


class OpenFinanceItemRead(BaseModel):
    id: str
    user_id: str
    provider: str
    external_item_id: str
    connector_name: str | None = None
    institution_name: str | None = None
    status: str
    consent_expires_at: datetime | None = None
    last_sync_at: datetime | None = None
    last_successful_sync_at: datetime | None = None
    last_error: str | None = None
    metadata: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime | None = None


class OpenFinanceSyncRunRead(BaseModel):
    id: str
    user_id: str
    provider: str
    external_item_id: str | None = None
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    accounts_created: int = 0
    accounts_updated: int = 0
    cards_created: int = 0
    cards_updated: int = 0
    transactions_created: int = 0
    transactions_updated: int = 0
    transactions_ignored: int = 0
    error_message: str | None = None
    metadata: dict[str, Any] = {}


class OpenFinanceSyncResponse(BaseModel):
    run: OpenFinanceSyncRunRead
    items: list[OpenFinanceItemRead] = []


class OpenFinanceWebhookResponse(BaseModel):
    status: str

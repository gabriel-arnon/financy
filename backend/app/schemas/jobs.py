from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


JobStatus = Literal["queued", "running", "success", "error", "canceled"]


class JobRunRead(BaseModel):
    id: str
    user_id: str
    kind: str
    status: JobStatus
    resource_type: str | None = None
    resource_id: str | None = None
    idempotency_key: str | None = None
    progress_current: int = 0
    progress_total: int | None = None
    error_message: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime | None = None

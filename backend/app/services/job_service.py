from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.errors import AppError
from app.schemas.jobs import JobRunRead


OPEN_FINANCE_SYNC_ITEM = "open_finance_sync_item"


class JobService:
    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def list(self, user_id: str, limit: int = 20) -> list[JobRunRead]:
        return [JobRunRead(**item) for item in self.repository.list_job_runs(user_id, limit=limit)]

    def get(self, user_id: str, job_id: str) -> JobRunRead:
        job = self.repository.get_job_run(user_id, job_id)
        if not job:
            raise AppError("Job nao encontrado.", status_code=404, code="job_not_found")
        return JobRunRead(**job)

    def create_open_finance_sync_item_job(self, user_id: str, external_item_id: str, provider: str = "pluggy") -> JobRunRead:
        today = datetime.now(UTC).date().isoformat()
        idempotency_key = f"{provider}:{external_item_id}:{today}"
        job = self.repository.create_job_run(
            user_id,
            {
                "kind": OPEN_FINANCE_SYNC_ITEM,
                "status": "queued",
                "resource_type": "open_finance_item",
                "resource_id": external_item_id,
                "idempotency_key": idempotency_key,
                "progress_current": 0,
                "progress_total": None,
                "result": {},
                "metadata": {
                    "provider": provider,
                    "external_item_id": external_item_id,
                    "created_from": "open_finance_sync_job_endpoint",
                },
                "queued_at": datetime.now(UTC),
            },
        )
        return JobRunRead(**job)

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.errors import AppError
from app.schemas.jobs import JobRunRead
from app.services.job_service import OPEN_FINANCE_SYNC_ITEM


class JobWorkerService:
    def __init__(self, repository: Any, open_finance_service: Any) -> None:
        self.repository = repository
        self.open_finance_service = open_finance_service

    def run_once(self) -> JobRunRead | None:
        job = self.repository.claim_next_job_run([OPEN_FINANCE_SYNC_ITEM])
        if not job:
            return None
        if job["kind"] == OPEN_FINANCE_SYNC_ITEM:
            return self._run_open_finance_sync_item(job)
        return self._finish_error(job, f"Tipo de job nao suportado: {job['kind']}")

    def _run_open_finance_sync_item(self, job: dict[str, Any]) -> JobRunRead:
        external_item_id = job.get("resource_id") or job.get("metadata", {}).get("external_item_id")
        if not external_item_id:
            return self._finish_error(job, "Job Open Finance sem item externo.")
        try:
            result = self.open_finance_service.sync_item(job["user_id"], str(external_item_id))
            return self._finish_success(job, self._open_finance_result(result))
        except AppError as exc:
            return self._finish_error(job, exc.message)
        except Exception as exc:  # pragma: no cover - defensive guard for worker runtime
            return self._finish_error(job, str(exc) or "Falha inesperada no job.")

    def _finish_success(self, job: dict[str, Any], result: dict[str, Any]) -> JobRunRead:
        finished = self.repository.update_job_run(
            job["user_id"],
            job["id"],
            {
                "status": "success",
                "progress_current": 1,
                "progress_total": 1,
                "result": result,
                "error_message": None,
                "finished_at": datetime.now(UTC),
            },
        )
        return JobRunRead(**(finished or job))

    def _finish_error(self, job: dict[str, Any], message: str) -> JobRunRead:
        finished = self.repository.update_job_run(
            job["user_id"],
            job["id"],
            {
                "status": "error",
                "error_message": message[:500],
                "finished_at": datetime.now(UTC),
            },
        )
        return JobRunRead(**(finished or job))

    def _open_finance_result(self, result: dict[str, Any]) -> dict[str, Any]:
        run = result.get("run", {}) if isinstance(result, dict) else {}
        items = result.get("items", []) if isinstance(result, dict) else []
        return {
            "sync_run_id": run.get("id"),
            "sync_status": run.get("status"),
            "items_count": len(items) if isinstance(items, list) else 0,
            "transactions_created": run.get("transactions_created", 0),
            "transactions_updated": run.get("transactions_updated", 0),
            "transactions_ignored": run.get("transactions_ignored", 0),
        }

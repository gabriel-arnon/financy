from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_job_service
from app.core.config import settings
from app.core.errors import AppError
from app.main import app
from app.repositories.local_json import LocalJsonRepository
from app.services.job_service import JobService, OPEN_FINANCE_SYNC_ITEM
from app.services.job_worker_service import JobWorkerService


def _job_service(tmp_path: Path) -> JobService:
    return JobService(LocalJsonRepository(tmp_path))


def test_open_finance_sync_item_job_is_idempotent_in_service(tmp_path: Path) -> None:
    service = _job_service(tmp_path)
    external_item_id = f"item-{uuid4()}"

    first = service.create_open_finance_sync_item_job(settings.dev_user_id, external_item_id)
    second = service.create_open_finance_sync_item_job(settings.dev_user_id, external_item_id)

    assert second.id == first.id
    assert first.kind == OPEN_FINANCE_SYNC_ITEM
    assert first.status == "queued"
    assert first.idempotency_key is not None
    assert len(service.list(settings.dev_user_id)) == 1


def test_job_worker_processes_open_finance_sync_job(tmp_path: Path) -> None:
    class FakeOpenFinanceService:
        def __init__(self) -> None:
            self.calls = []

        def sync_item(self, user_id: str, external_item_id: str):
            self.calls.append((user_id, external_item_id))
            return {
                "run": {
                    "id": "sync-run-1",
                    "status": "success",
                    "transactions_created": 3,
                    "transactions_updated": 1,
                    "transactions_ignored": 0,
                },
                "items": [{"id": "item-1"}],
            }

    repo = LocalJsonRepository(tmp_path)
    service = JobService(repo)
    job = service.create_open_finance_sync_item_job(settings.dev_user_id, f"item-{uuid4()}")
    open_finance = FakeOpenFinanceService()

    processed = JobWorkerService(repo, open_finance).run_once()

    assert processed is not None
    assert processed.id == job.id
    assert processed.status == "success"
    assert processed.result["sync_run_id"] == "sync-run-1"
    assert processed.result["transactions_created"] == 3
    assert open_finance.calls == [(settings.dev_user_id, job.resource_id)]


def test_job_worker_marks_open_finance_errors(tmp_path: Path) -> None:
    class FakeOpenFinanceService:
        def sync_item(self, user_id: str, external_item_id: str):
            raise AppError("Credenciais Open Finance nao configuradas.", status_code=400, code="open_finance_not_configured")

    repo = LocalJsonRepository(tmp_path)
    service = JobService(repo)
    job = service.create_open_finance_sync_item_job(settings.dev_user_id, f"item-{uuid4()}")

    processed = JobWorkerService(repo, FakeOpenFinanceService()).run_once()

    assert processed is not None
    assert processed.id == job.id
    assert processed.status == "error"
    assert processed.error_message == "Credenciais Open Finance nao configuradas."


def test_job_worker_returns_none_without_queued_jobs(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)

    assert JobWorkerService(repo, object()).run_once() is None


def test_job_service_does_not_return_other_user_job(tmp_path: Path) -> None:
    service = _job_service(tmp_path)
    job = service.create_open_finance_sync_item_job(settings.dev_user_id, f"item-{uuid4()}")

    with pytest.raises(AppError) as exc_info:
        service.get("00000000-0000-4000-8000-000000009999", job.id)

    assert exc_info.value.code == "job_not_found"


def test_jobs_api_lists_and_gets_user_jobs(tmp_path: Path) -> None:
    service = _job_service(tmp_path)
    job = service.create_open_finance_sync_item_job(settings.dev_user_id, f"item-{uuid4()}")
    app.dependency_overrides[get_job_service] = lambda: service
    try:
        client = TestClient(app)
        list_response = client.get("/jobs")
        get_response = client.get(f"/jobs/{job.id}")
    finally:
        app.dependency_overrides.pop(get_job_service, None)

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [job.id]
    assert get_response.status_code == 200
    assert get_response.json()["id"] == job.id


def test_open_finance_sync_jobs_endpoint_reuses_same_daily_job(tmp_path: Path, monkeypatch) -> None:
    service = _job_service(tmp_path)
    external_item_id = f"item-{uuid4()}"
    monkeypatch.setattr(settings, "open_finance_enabled", True)
    monkeypatch.setattr(settings, "open_finance_owner_user_id", settings.dev_user_id)
    app.dependency_overrides[get_job_service] = lambda: service
    try:
        client = TestClient(app)
        first_response = client.post(f"/open-finance/items/{external_item_id}/sync-jobs")
        second_response = client.post(f"/open-finance/items/{external_item_id}/sync-jobs")
    finally:
        app.dependency_overrides.pop(get_job_service, None)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first = first_response.json()
    second = second_response.json()
    assert second["id"] == first["id"]
    assert first["kind"] == OPEN_FINANCE_SYNC_ITEM
    assert first["status"] == "queued"
    assert first["resource_type"] == "open_finance_item"
    assert first["resource_id"] == external_item_id
    assert first["idempotency_key"].startswith(f"pluggy:{external_item_id}:")
    assert len(service.list(settings.dev_user_id)) == 1

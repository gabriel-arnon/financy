from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID
from uuid import uuid4

from psycopg.types.json import Jsonb


def _adapt_job_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (dict, list)):
        return Jsonb(value)
    return value


def _normalize_job_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    return value


def _job_record(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: _normalize_job_value(value) for key, value in row.items()}


class PostgresJobsMixin:
    def create_job_run(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        now = datetime.now(timezone.utc)
        data = {
            "id": payload.get("id") or str(uuid4()),
            "user_id": user_id,
            "status": "queued",
            "progress_current": 0,
            "result": {},
            "metadata": {},
            "queued_at": now,
            **payload,
        }
        columns = [
            "id",
            "user_id",
            "kind",
            "status",
            "resource_type",
            "resource_id",
            "idempotency_key",
            "progress_current",
            "progress_total",
            "error_message",
            "result",
            "metadata",
            "queued_at",
            "started_at",
            "finished_at",
            "updated_at",
        ]
        names = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        values = tuple(_adapt_job_value(data.get(column)) for column in columns)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                insert into job_runs ({names})
                values ({placeholders})
                on conflict (user_id, kind, idempotency_key)
                where idempotency_key is not null
                do update set updated_at = job_runs.updated_at
                returning *
                """,
                values,
            )
            return _job_record(cur.fetchone()) or {}

    def get_job_run(self, user_id: str, job_id: str) -> dict[str, Any] | None:
        return self._fetch_one("select * from job_runs where id = %s and user_id = %s", (job_id, user_id))

    def list_job_runs(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select * from job_runs
            where user_id = %s
            order by queued_at desc
            limit %s
            """,
            (user_id, limit),
        )

    def claim_next_job_run(self, kinds: list[str]) -> dict[str, Any] | None:
        if not kinds:
            return None
        placeholders = ", ".join(["%s"] * len(kinds))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                update job_runs
                set status = 'running',
                    started_at = coalesce(started_at, now()),
                    updated_at = now()
                where id = (
                  select id
                  from job_runs
                  where status = 'queued' and kind in ({placeholders})
                  order by queued_at asc
                  for update skip locked
                  limit 1
                )
                returning *
                """,
                tuple(kinds),
            )
            return _job_record(cur.fetchone())

    def update_job_run(self, user_id: str, job_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update(
            "job_runs",
            {**payload, "updated_at": datetime.now(timezone.utc)},
            "id = %s and user_id = %s",
            (job_id, user_id),
        )

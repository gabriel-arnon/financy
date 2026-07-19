from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.parsers.utils import normalize_description


class PostgresPayeesMixin:
    def list_payees(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            "select * from payees where user_id = %s and status = 'active' order by canonical_name",
            (user_id,),
        )

    def create_payee(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        return self._insert(
            "payees",
            {
                "id": payload.get("id") or str(uuid4()),
                "user_id": user_id,
                "metadata": {},
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def list_payee_aliases(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select ma.*, p.canonical_name
            from merchant_aliases ma
            join payees p on p.id = ma.payee_id and p.user_id = ma.user_id
            where ma.user_id = %s and ma.status = 'active' and p.status = 'active'
            order by length(ma.normalized_alias) desc, ma.created_at desc
            """,
            (user_id,),
        )

    def create_payee_alias(self, user_id: str, payee_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        alias = str(payload.get("alias") or "")
        return self._insert(
            "merchant_aliases",
            {
                "id": payload.get("id") or str(uuid4()),
                "user_id": user_id,
                "payee_id": payee_id,
                "alias": alias,
                "normalized_alias": payload.get("normalized_alias") or normalize_description(alias),
                "source": "manual",
                "status": "active",
                "metadata": {},
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

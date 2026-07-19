from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class PostgresAccountsCardsMixin:
    def list_accounts(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            "select * from accounts where user_id = %s and status = 'active' order by created_at desc",
            (user_id,),
        )

    def _all_accounts(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all("select * from accounts where user_id = %s order by created_at desc", (user_id,))

    def get_account(self, user_id: str, account_id: str) -> dict[str, Any] | None:
        return self._fetch_one("select * from accounts where id = %s and user_id = %s", (account_id, user_id))

    def create_account(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        return self._insert(
            "accounts",
            {
                "id": payload.get("id") or str(uuid4()),
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def update_account(self, user_id: str, account_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update("accounts", payload, "id = %s and user_id = %s", (account_id, user_id))

    def delete_account(self, user_id: str, account_id: str) -> dict[str, Any] | None:
        return self.update_account(user_id, account_id, {"status": "inactive"})

    def list_cards(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            "select * from cards where user_id = %s and status = 'active' order by created_at desc",
            (user_id,),
        )

    def _all_cards(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all("select * from cards where user_id = %s order by created_at desc", (user_id,))

    def get_card(self, user_id: str, card_id: str) -> dict[str, Any] | None:
        return self._fetch_one("select * from cards where id = %s and user_id = %s", (card_id, user_id))

    def create_card(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        return self._insert(
            "cards",
            {
                "id": payload.get("id") or str(uuid4()),
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def update_card(self, user_id: str, card_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update("cards", payload, "id = %s and user_id = %s", (card_id, user_id))

    def delete_card(self, user_id: str, card_id: str) -> dict[str, Any] | None:
        return self.update_card(user_id, card_id, {"status": "inactive"})

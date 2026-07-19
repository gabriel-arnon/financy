from __future__ import annotations

from typing import Any, Protocol

from app.services.pluggy_client import PluggyClient


class OpenFinanceProvider(Protocol):
    provider_name: str

    def create_connect_token(self, client_user_id: str) -> str: ...

    def get_item(self, item_id: str) -> dict[str, Any]: ...

    def list_items(self) -> list[dict[str, Any]]: ...

    def list_accounts(self, item_id: str) -> list[dict[str, Any]]: ...

    def list_transactions(self, account_id: str, *, from_date: str | None = None, to_date: str | None = None) -> list[dict[str, Any]]: ...

    def list_investments(self, item_id: str) -> list[dict[str, Any]]: ...


class PluggyOpenFinanceProvider:
    provider_name = "pluggy"

    def __init__(self, client: PluggyClient) -> None:
        self.client = client

    def create_connect_token(self, client_user_id: str) -> str:
        return self.client.create_connect_token(client_user_id)

    def get_item(self, item_id: str) -> dict[str, Any]:
        return self.client.get_item(item_id)

    def list_items(self) -> list[dict[str, Any]]:
        return self.client.list_items()

    def list_accounts(self, item_id: str) -> list[dict[str, Any]]:
        return self.client.list_accounts(item_id)

    def list_transactions(self, account_id: str, *, from_date: str | None = None, to_date: str | None = None) -> list[dict[str, Any]]:
        return self.client.list_transactions(account_id, from_date=from_date, to_date=to_date)

    def list_investments(self, item_id: str) -> list[dict[str, Any]]:
        return self.client.list_investments(item_id)

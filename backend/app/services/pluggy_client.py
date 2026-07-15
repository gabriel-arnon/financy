from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


class PluggyClientError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class PluggyClient:
    def __init__(self, settings) -> None:
        self.settings = settings
        self._api_key: str | None = None
        self._api_key_expires_at: datetime | None = None

    def _base_url(self) -> str:
        return self.settings.pluggy_base_url.rstrip("/")

    def _require_credentials(self) -> tuple[str, str]:
        if not self.settings.pluggy_client_id or not self.settings.pluggy_client_secret:
            raise PluggyClientError("Credenciais Pluggy nao configuradas.")
        return self.settings.pluggy_client_id, self.settings.pluggy_client_secret

    def _request(self, method: str, path: str, *, headers: dict[str, str] | None = None, **kwargs: Any) -> Any:
        url = f"{self._base_url()}{path}"
        try:
            with httpx.Client(timeout=self.settings.pluggy_api_timeout_seconds) as client:
                response = client.request(method, url, headers=headers, **kwargs)
        except httpx.TimeoutException as exc:
            raise PluggyClientError("Tempo esgotado ao chamar a Pluggy.") from exc
        except httpx.HTTPError as exc:
            raise PluggyClientError("Falha de conexao com a Pluggy.") from exc
        if response.status_code >= 400:
            raise PluggyClientError(f"Pluggy retornou HTTP {response.status_code}.", status_code=response.status_code)
        return response.json()

    def authenticate(self, *, force: bool = False) -> str:
        now = datetime.now(timezone.utc)
        if not force and self._api_key and self._api_key_expires_at and self._api_key_expires_at > now + timedelta(minutes=5):
            return self._api_key
        client_id, client_secret = self._require_credentials()
        payload = self._request(
            "POST",
            "/auth",
            json={"clientId": client_id, "clientSecret": client_secret},
        )
        api_key = payload.get("apiKey") or payload.get("accessToken") or payload.get("token")
        if not api_key:
            raise PluggyClientError("Resposta de autenticacao Pluggy sem apiKey.")
        expires_in = int(payload.get("expiresIn") or 7200)
        self._api_key = str(api_key)
        self._api_key_expires_at = now + timedelta(seconds=max(60, expires_in))
        return self._api_key

    def _headers(self) -> dict[str, str]:
        return {"X-API-KEY": self.authenticate()}

    def _paginated_get(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        page = 1
        results: list[dict[str, Any]] = []
        while True:
            query = {**(params or {}), "page": page}
            payload = self._request("GET", path, headers=self._headers(), params=query)
            batch = payload.get("results") if isinstance(payload, dict) else payload
            if not isinstance(batch, list):
                return results
            results.extend([item for item in batch if isinstance(item, dict)])
            total_pages = int(payload.get("totalPages") or payload.get("pages") or page) if isinstance(payload, dict) else page
            if page >= total_pages or not batch:
                return results
            page += 1

    def get_item(self, item_id: str) -> dict[str, Any]:
        return self._request("GET", f"/items/{item_id}", headers=self._headers())

    def list_items(self) -> list[dict[str, Any]]:
        return self._paginated_get("/items")

    def list_accounts(self, item_id: str) -> list[dict[str, Any]]:
        return self._paginated_get("/accounts", {"itemId": item_id})

    def list_transactions(self, account_id: str, *, from_date: str | None = None, to_date: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"accountId": account_id}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return self._paginated_get("/transactions", params)

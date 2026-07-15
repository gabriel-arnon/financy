from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from threading import Lock
from time import perf_counter
from typing import Any

from app.core.errors import AppError
from app.parsers.utils import normalize_description
from app.services.pluggy_client import PluggyClientError


PROVIDER = "pluggy"


def _safe_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return message[:300]


def _decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    if isinstance(value, dict):
        value = value.get("amount") or value.get("value") or value.get("current")
    try:
        return Decimal(str(value if value not in (None, "") else default)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return default


def _digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _iso_date(value: Any) -> str:
    if not value:
        return datetime.now(timezone.utc).date().isoformat()
    text = str(value)
    return text[:10]


class OpenFinanceService:
    _sync_locks_guard = Lock()
    _sync_locks: dict[tuple[str, str], Lock] = {}

    def __init__(self, repository, settings, pluggy_client) -> None:
        self.repository = repository
        self.settings = settings
        self.pluggy_client = pluggy_client

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.settings.open_finance_enabled,
            "owner_only": True,
            "configured": self.settings.open_finance_configured,
            "provider": PROVIDER,
        }

    def ensure_owner(self, user_id: str) -> None:
        if not self.settings.open_finance_enabled:
            raise AppError("Open Finance nao esta habilitado.", status_code=404, code="open_finance_disabled")
        if not self.settings.open_finance_owner_user_id or user_id != self.settings.open_finance_owner_user_id:
            raise AppError("Open Finance nao encontrado.", status_code=404, code="open_finance_not_found")

    def ensure_configured(self) -> None:
        if not self.settings.open_finance_configured:
            raise AppError("Credenciais Open Finance nao configuradas.", status_code=400, code="open_finance_not_configured")

    def list_items(self, user_id: str) -> list[dict[str, Any]]:
        self.ensure_owner(user_id)
        return self.repository.list_open_finance_items(user_id)

    def list_sync_runs(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        self.ensure_owner(user_id)
        return self.repository.list_open_finance_sync_runs(user_id, limit=limit)

    def register_item(self, user_id: str, external_item_id: str) -> dict[str, Any]:
        self.ensure_owner(user_id)
        self.ensure_configured()
        item_payload = self._fetch_item_metadata(external_item_id)
        return self.repository.upsert_open_finance_item(user_id, item_payload)

    def sync_all(self, user_id: str) -> dict[str, Any]:
        self.ensure_owner(user_id)
        self.ensure_configured()
        items = self.repository.list_open_finance_items(user_id)
        if not items:
            remote_items = self.pluggy_client.list_items()
            items = [
                self.repository.upsert_open_finance_item(user_id, self._item_payload(item.get("id") or item.get("itemId"), item))
                for item in remote_items
                if item.get("id") or item.get("itemId")
            ]
        totals = None
        updated_items = []
        for item in items:
            result = self.sync_item(user_id, item["external_item_id"])
            updated_items.extend(result["items"])
            totals = result["run"]
        if totals is None:
            run = self.repository.create_open_finance_sync_run(user_id, {"status": "success", "external_item_id": None})
            run = self.repository.update_open_finance_sync_run(
                user_id,
                run["id"],
                {"finished_at": datetime.now(timezone.utc).isoformat(), "duration_ms": 0},
            )
            totals = run
        return {"run": totals, "items": updated_items}

    def sync_item(self, user_id: str, external_item_id: str) -> dict[str, Any]:
        self.ensure_owner(user_id)
        self.ensure_configured()
        lock_key = (user_id, external_item_id)
        with self._sync_locks_guard:
            lock = self._sync_locks.setdefault(lock_key, Lock())
        if not lock.acquire(blocking=False):
            raise AppError("Sincronizacao Open Finance ja em andamento.", status_code=409, code="open_finance_sync_in_progress")
        try:
            return self._sync_item_locked(user_id, external_item_id)
        finally:
            lock.release()

    def _sync_item_locked(self, user_id: str, external_item_id: str) -> dict[str, Any]:
        started = perf_counter()
        run = self.repository.create_open_finance_sync_run(
            user_id,
            {"status": "running", "external_item_id": external_item_id, "provider": PROVIDER},
        )
        counters = {
            "accounts_created": 0,
            "accounts_updated": 0,
            "cards_created": 0,
            "cards_updated": 0,
            "transactions_created": 0,
            "transactions_updated": 0,
            "transactions_ignored": 0,
        }
        try:
            item = self.repository.upsert_open_finance_item(user_id, self._fetch_item_metadata(external_item_id))
            from_date = (datetime.now(timezone.utc).date() - timedelta(days=self.settings.pluggy_sync_lookback_days)).isoformat()
            accounts = self.pluggy_client.list_accounts(external_item_id)
            for account in accounts:
                link = self._sync_account(user_id, item, account, counters)
                try:
                    transactions = self.pluggy_client.list_transactions(str(account.get("id")), from_date=from_date)
                except PluggyClientError as exc:
                    if exc.status_code == 410:
                        counters["transactions_ignored"] += 1
                        continue
                    raise
                for transaction in transactions:
                    self._sync_transaction(user_id, item, link, transaction, counters)
            now = datetime.now(timezone.utc)
            item = self.repository.upsert_open_finance_item(
                user_id,
                {
                    **item,
                    "last_sync_at": now.isoformat(),
                    "last_successful_sync_at": now.isoformat(),
                    "last_error": None,
                },
            )
            final = self.repository.update_open_finance_sync_run(
                user_id,
                run["id"],
                {
                    "status": "success",
                    "finished_at": now.isoformat(),
                    "duration_ms": int((perf_counter() - started) * 1000),
                    **counters,
                },
            )
            return {"run": final, "items": [item]}
        except (PluggyClientError, AppError, Exception) as exc:
            now = datetime.now(timezone.utc)
            error = _safe_error(exc)
            self.repository.upsert_open_finance_item(
                user_id,
                {
                    "provider": PROVIDER,
                    "external_item_id": external_item_id,
                    "status": "error",
                    "last_sync_at": now.isoformat(),
                    "last_error": error,
                    "metadata": {},
                },
            )
            final = self.repository.update_open_finance_sync_run(
                user_id,
                run["id"],
                {
                    "status": "error",
                    "finished_at": now.isoformat(),
                    "duration_ms": int((perf_counter() - started) * 1000),
                    "error_message": error,
                    **counters,
                },
            )
            if isinstance(exc, AppError):
                raise
            raise AppError("Falha ao sincronizar Open Finance.", status_code=502, code="open_finance_sync_failed") from exc

    def _fetch_item_metadata(self, external_item_id: str) -> dict[str, Any]:
        return self._item_payload(external_item_id, self.pluggy_client.get_item(external_item_id))

    def _item_payload(self, external_item_id: Any, item: dict[str, Any]) -> dict[str, Any]:
        connector = item.get("connector") if isinstance(item.get("connector"), dict) else {}
        institution = item.get("institution") if isinstance(item.get("institution"), dict) else {}
        return {
            "provider": PROVIDER,
            "external_item_id": str(external_item_id),
            "connector_name": connector.get("name") or item.get("connectorName"),
            "institution_name": institution.get("name") or connector.get("institutionName") or item.get("institutionName"),
            "status": str(item.get("status") or "active").lower(),
            "consent_expires_at": item.get("consentExpiresAt") or item.get("expiresAt"),
            "metadata": {"raw_status": item.get("status"), "execution_status": item.get("executionStatus")},
        }

    def _sync_account(self, user_id: str, item: dict[str, Any], account: dict[str, Any], counters: dict[str, int]) -> dict[str, Any]:
        external_account_id = str(account.get("id"))
        account_type = str(account.get("type") or account.get("subtype") or "").upper()
        name = str(account.get("name") or account.get("marketingName") or account.get("number") or "Open Finance")
        institution_name = item.get("institution_name") or account.get("institutionName")
        existing = self.repository.get_open_finance_account_link(user_id, PROVIDER, external_account_id)
        last_digits = (_digits(account.get("number")) or _digits(account.get("creditData", {}).get("number")) or external_account_id)[-4:]
        if not last_digits.isdigit() or len(last_digits) != 4:
            last_digits = "0000"
        if "CREDIT" in account_type or "CARD" in account_type:
            payload = {
                "name": name,
                "institution": institution_name,
                "brand": account.get("brand"),
                "last_digits": last_digits,
                "limit_amount": str(_decimal(account.get("creditLimit") or account.get("limit"), Decimal("0"))),
                "closing_day": None,
                "due_day": None,
                "status": "active",
                "external_source": "open_finance",
            }
            if existing and existing.get("card_id"):
                card = self.repository.update_card(user_id, existing["card_id"], payload)
                counters["cards_updated"] += 1
            else:
                card = self.repository.create_card(user_id, payload)
                counters["cards_created"] += 1
            return self.repository.upsert_open_finance_account_link(
                user_id,
                {
                    "provider": PROVIDER,
                    "external_account_id": external_account_id,
                    "open_finance_item_id": item["id"],
                    "card_id": card["id"],
                    "account_id": None,
                    "account_type": account.get("type"),
                    "subtype": account.get("subtype"),
                    "display_name": name,
                    "institution_name": institution_name,
                    "last_digits": last_digits,
                    "metadata": {"raw_type": account.get("type")},
                },
            )
        payload = {
            "name": name,
            "institution": institution_name,
            "agency": account.get("branchCode") or account.get("agency"),
            "account_number": account.get("number"),
            "type": self._account_type(account_type),
            "balance": str(_decimal(account.get("balance"))),
            "status": "active",
            "external_source": "open_finance",
        }
        if existing and existing.get("account_id"):
            local_account = self.repository.update_account(user_id, existing["account_id"], payload)
            counters["accounts_updated"] += 1
        else:
            local_account = self.repository.create_account(user_id, payload)
            counters["accounts_created"] += 1
        return self.repository.upsert_open_finance_account_link(
            user_id,
            {
                "provider": PROVIDER,
                "external_account_id": external_account_id,
                "open_finance_item_id": item["id"],
                "account_id": local_account["id"],
                "card_id": None,
                "account_type": account.get("type"),
                "subtype": account.get("subtype"),
                "display_name": name,
                "institution_name": institution_name,
                "last_digits": last_digits,
                "metadata": {"raw_type": account.get("type")},
            },
        )

    def _account_type(self, account_type: str) -> str:
        if "SAV" in account_type:
            return "savings"
        if "INVEST" in account_type:
            return "investment"
        return "checking"

    def _sync_transaction(self, user_id: str, item: dict[str, Any], link: dict[str, Any], transaction: dict[str, Any], counters: dict[str, int]) -> None:
        external_transaction_id = str(transaction.get("id") or "")
        if not external_transaction_id:
            counters["transactions_ignored"] += 1
            return
        existing = self.repository.get_open_finance_transaction_link(user_id, PROVIDER, external_transaction_id)
        description = str(transaction.get("description") or transaction.get("merchant", {}).get("name") or "Open Finance")
        tx_type = self._transaction_type(transaction)
        payload = {
            "account_id": link.get("account_id"),
            "card_id": link.get("card_id"),
            "card_statement_id": None,
            "transaction_date": _iso_date(transaction.get("date") or transaction.get("postedDate") or transaction.get("createdAt")),
            "description": description,
            "original_description": str(transaction.get("description") or description),
            "normalized_description": normalize_description(description),
            "amount": str(abs(_decimal(transaction.get("amount") or transaction.get("value")))),
            "type": tx_type,
            "category_id": None,
            "source_file_id": None,
            "installment_current": None,
            "installment_total": None,
            "status": "confirmed",
            "external_source": "open_finance",
        }
        rule = self.repository.match_classification_rule(user_id, payload["description"], payload["original_description"], tx_type)
        if rule:
            payload["category_id"] = rule["category_id"]
        if existing:
            self.repository.update_transaction(user_id, existing["transaction_id"], payload)
            counters["transactions_updated"] += 1
            transaction_id = existing["transaction_id"]
        elif self.repository.transaction_signature_exists({"user_id": user_id, **payload}):
            counters["transactions_ignored"] += 1
            return
        else:
            created = self.repository.create_transaction(user_id, payload)
            transaction_id = created["id"]
            counters["transactions_created"] += 1
        self.repository.upsert_open_finance_transaction_link(
            user_id,
            {
                "provider": PROVIDER,
                "external_transaction_id": external_transaction_id,
                "external_account_id": link.get("external_account_id"),
                "open_finance_item_id": item["id"],
                "transaction_id": transaction_id,
                "metadata": {"raw_type": transaction.get("type")},
            },
        )

    def _transaction_type(self, transaction: dict[str, Any]) -> str:
        raw_type = str(transaction.get("type") or transaction.get("operationType") or "").upper()
        amount = _decimal(transaction.get("amount") or transaction.get("value"))
        if "TRANSFER" in raw_type:
            return "transfer"
        if "PAYMENT" in raw_type:
            return "payment"
        if "REFUND" in raw_type:
            return "refund"
        if "CREDIT" in raw_type or amount > 0:
            return "income"
        return "expense"

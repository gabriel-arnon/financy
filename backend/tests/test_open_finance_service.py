from threading import Thread
from time import sleep
from types import SimpleNamespace

from app.core.errors import AppError
from app.repositories.local_json import LocalJsonRepository
from app.services.open_finance_service import OpenFinanceService
from app.services.pluggy_client import PluggyClientError


OWNER_ID = "00000000-0000-4000-8000-000000000777"


class FakePluggyClient:
    def get_item(self, item_id: str):
        return {
            "id": item_id,
            "status": "UPDATED",
            "connector": {"name": "Meu Pluggy", "institutionName": "Banco Teste"},
        }

    def list_items(self):
        return [self.get_item("item-1")]

    def list_accounts(self, item_id: str):
        return [
            {
                "id": "account-1",
                "name": "Conta Pluggy",
                "type": "BANK",
                "subtype": "CHECKING_ACCOUNT",
                "number": "123456-7",
                "balance": {"amount": "1000.00"},
            }
        ]

    def list_transactions(self, account_id: str, **kwargs):
        return [
            {
                "id": "tx-1",
                "date": "2026-07-01",
                "description": "IFOOD TESTE",
                "amount": "-55.90",
                "type": "DEBIT",
            }
        ]


def settings():
    return SimpleNamespace(
        open_finance_enabled=True,
        open_finance_owner_user_id=OWNER_ID,
        open_finance_configured=True,
        pluggy_sync_lookback_days=30,
    )


def test_sync_item_imports_accounts_and_transactions_idempotently(tmp_path) -> None:
    repository = LocalJsonRepository(tmp_path)
    service = OpenFinanceService(repository=repository, settings=settings(), pluggy_client=FakePluggyClient())

    first = service.sync_item(OWNER_ID, "item-1")
    second = service.sync_item(OWNER_ID, "item-1")

    transactions = repository.list_transactions(OWNER_ID)
    accounts = repository.list_accounts(OWNER_ID)

    assert first["run"]["transactions_created"] == 1
    assert second["run"]["transactions_updated"] == 1
    assert len(transactions) == 1
    assert len(accounts) == 1
    assert transactions[0]["description"] == "IFOOD TESTE"
    assert transactions[0]["amount"] == "55.90"
    assert transactions[0]["type"] == "expense"
    assert transactions[0]["external_source"] == "open_finance"
    assert accounts[0]["external_source"] == "open_finance"


def test_sync_all_registers_remote_items_when_none_exist(tmp_path) -> None:
    repository = LocalJsonRepository(tmp_path)
    service = OpenFinanceService(repository=repository, settings=settings(), pluggy_client=FakePluggyClient())

    result = service.sync_all(OWNER_ID)

    assert result["run"]["status"] == "success"
    assert repository.list_open_finance_items(OWNER_ID)[0]["external_item_id"] == "item-1"


def test_sync_item_blocks_concurrent_sync_for_same_item(tmp_path) -> None:
    class SlowPluggyClient(FakePluggyClient):
        def list_accounts(self, item_id: str):
            sleep(0.2)
            return super().list_accounts(item_id)

    repository = LocalJsonRepository(tmp_path)
    service = OpenFinanceService(repository=repository, settings=settings(), pluggy_client=SlowPluggyClient())
    results = []

    def run_sync() -> None:
        try:
            results.append(service.sync_item(OWNER_ID, "item-1")["run"]["status"])
        except AppError as exc:
            results.append(exc.code)

    first = Thread(target=run_sync)
    second = Thread(target=run_sync)
    first.start()
    sleep(0.05)
    second.start()
    first.join(timeout=5)
    second.join(timeout=5)

    assert "success" in results
    assert "open_finance_sync_in_progress" in results


def test_sync_item_skips_account_transactions_when_pluggy_returns_410(tmp_path) -> None:
    class GoneTransactionsPluggyClient(FakePluggyClient):
        def list_transactions(self, account_id: str, **kwargs):
            raise PluggyClientError("Pluggy retornou HTTP 410 em GET /transactions.", status_code=410, path="/transactions")

    repository = LocalJsonRepository(tmp_path)
    service = OpenFinanceService(repository=repository, settings=settings(), pluggy_client=GoneTransactionsPluggyClient())

    result = service.sync_item(OWNER_ID, "item-1")

    assert result["run"]["status"] == "success"
    assert result["run"]["transactions_ignored"] == 1
    assert repository.list_accounts(OWNER_ID)[0]["name"] == "Conta Pluggy"
    assert repository.list_transactions(OWNER_ID) == []

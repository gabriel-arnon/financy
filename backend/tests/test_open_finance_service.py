from threading import Thread
from time import sleep
from types import SimpleNamespace

from app.core.errors import AppError
from app.repositories.local_json import LocalJsonRepository
from app.services.open_finance_service import OpenFinanceService
from app.services.pluggy_client import PluggyClientError


OWNER_ID = "00000000-0000-4000-8000-000000000777"


class FakePluggyClient:
    def create_connect_token(self, client_user_id: str):
        return f"connect-{client_user_id}"

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
    assert first["run"]["metadata"]["accounts_found"] == 1
    assert first["run"]["metadata"]["transactions_found"] == 1
    assert len(transactions) == 1
    assert len(accounts) == 1
    assert transactions[0]["description"] == "IFOOD TESTE"
    assert transactions[0]["amount"] == "55.90"
    assert transactions[0]["type"] == "expense"
    assert transactions[0]["external_source"] == "open_finance"
    assert accounts[0]["external_source"] == "open_finance"


def test_create_connect_token_uses_owner_user_id(tmp_path) -> None:
    repository = LocalJsonRepository(tmp_path)
    service = OpenFinanceService(repository=repository, settings=settings(), pluggy_client=FakePluggyClient())

    assert service.create_connect_token(OWNER_ID) == {"connect_token": f"connect-{OWNER_ID}"}


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
    assert result["run"]["metadata"]["transactions_ignored_reasons"] == {"transactions_unavailable": 1}
    assert repository.list_accounts(OWNER_ID)[0]["name"] == "Conta Pluggy"
    assert repository.list_transactions(OWNER_ID) == []


def test_sync_item_imports_transaction_without_provider_id_using_stable_fallback(tmp_path) -> None:
    class TransactionWithoutIdPluggyClient(FakePluggyClient):
        def list_transactions(self, account_id: str, **kwargs):
            return [
                {
                    "accountId": account_id,
                    "date": "2026-07-03",
                    "description": "PIX TESTE",
                    "amount": "-12.34",
                    "providerCode": "PIX",
                    "currencyCode": "BRL",
                    "balance": "987.66",
                }
            ]

    repository = LocalJsonRepository(tmp_path)
    service = OpenFinanceService(repository=repository, settings=settings(), pluggy_client=TransactionWithoutIdPluggyClient())

    first = service.sync_item(OWNER_ID, "item-1")
    second = service.sync_item(OWNER_ID, "item-1")

    transactions = repository.list_transactions(OWNER_ID)
    links = repository._read()["open_finance_transaction_links"]
    assert first["run"]["transactions_created"] == 1
    assert second["run"]["transactions_updated"] == 1
    assert first["run"]["metadata"]["transactions_found"] == 1
    assert len(transactions) == 1
    assert transactions[0]["description"] == "PIX TESTE"
    assert links[0]["metadata"]["provider_code"] == "PIX"
    assert links[0]["metadata"]["currency_code"] == "BRL"
    assert links[0]["metadata"]["balance_after_transaction"] == "987.66"


def test_sync_item_maps_credit_data_into_card_and_metadata(tmp_path) -> None:
    class CreditCardPluggyClient(FakePluggyClient):
        def list_accounts(self, item_id: str):
            return [
                {
                    "id": "credit-1",
                    "itemId": item_id,
                    "name": "Cartao Black",
                    "type": "CREDIT",
                    "subtype": "CREDIT_CARD",
                    "number": "9999888877776666",
                    "balance": "-120.00",
                    "currencyCode": "BRL",
                    "owner": "Owner Teste",
                    "taxNumber": "12345678900",
                    "creditData": {
                        "brand": "Visa",
                        "creditLimit": 5000,
                        "availableCreditLimit": 4880,
                        "balanceCloseDate": "2026-07-20",
                        "balanceDueDate": "2026-07-28",
                    },
                }
            ]

        def list_transactions(self, account_id: str, **kwargs):
            return []

    repository = LocalJsonRepository(tmp_path)
    service = OpenFinanceService(repository=repository, settings=settings(), pluggy_client=CreditCardPluggyClient())

    result = service.sync_item(OWNER_ID, "item-1")

    card = repository.list_cards(OWNER_ID)[0]
    link = repository._read()["open_finance_account_links"][0]
    assert result["run"]["cards_created"] == 1
    assert card["brand"] == "Visa"
    assert card["limit_amount"] == "5000.00"
    assert card["closing_day"] == 20
    assert card["due_day"] == 28
    assert link["metadata"]["currency_code"] == "BRL"
    assert link["metadata"]["owner"] == "Owner Teste"
    assert link["metadata"]["credit_data"]["availableCreditLimit"] == 4880

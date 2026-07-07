from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import repository
from app.core.config import settings
from app.main import app
from app.repositories.local_json import LocalJsonRepository


def test_legacy_accounts_and_cards_without_status_are_listed(tmp_path) -> None:
    repo = LocalJsonRepository(tmp_path)
    user_id = settings.dev_user_id

    account = repo.create_account(
        user_id,
        {
            "name": "Conta Legada",
            "institution": "Banco Legado",
            "type": "checking",
            "balance": "0",
        },
    )
    inactive_account = repo.create_account(
        user_id,
        {
            "name": "Conta Inativa",
            "institution": "Banco Legado",
            "type": "checking",
            "balance": "0",
            "status": "inactive",
        },
    )
    card = repo.create_card(
        user_id,
        {
            "account_id": account["id"],
            "name": "Cartao Legado",
            "institution": "Banco Legado",
            "brand": "Visa",
            "last_digits": "1234",
        },
    )
    inactive_card = repo.create_card(
        user_id,
        {
            "account_id": account["id"],
            "name": "Cartao Inativo",
            "institution": "Banco Legado",
            "brand": "Visa",
            "last_digits": "5678",
            "status": "inactive",
        },
    )

    assert account["id"] in {item["id"] for item in repo.list_accounts(user_id)}
    assert inactive_account["id"] not in {item["id"] for item in repo.list_accounts(user_id)}
    assert card["id"] in {item["id"] for item in repo.list_cards(user_id)}
    assert inactive_card["id"] not in {item["id"] for item in repo.list_cards(user_id)}


def test_accounts_crud_soft_delete() -> None:
    client = TestClient(app)

    created = client.post(
        "/accounts",
        json={
            "name": "Conta Principal",
            "institution": "Banco do Brasil",
            "type": "checking",
            "balance": "123.45",
            "status": "active",
        },
    )
    assert created.status_code == 200
    account = created.json()
    assert account["institution"] == "Banco do Brasil"

    updated = client.put(f"/accounts/{account['id']}", json={"name": "Conta Editada", "balance": "200.00"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Conta Editada"

    deleted = client.delete(f"/accounts/{account['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "inactive"

    listed = client.get("/accounts")
    assert listed.status_code == 200
    assert account["id"] not in {item["id"] for item in listed.json()}


def test_cards_crud_validation_and_soft_delete() -> None:
    client = TestClient(app)
    account = client.post(
        "/accounts",
        json={
            "name": "Conta Cartao",
            "institution": "Banco do Brasil",
            "type": "checking",
            "balance": "0",
            "status": "active",
        },
    ).json()

    invalid_digits = client.post(
        "/cards",
        json={
            "account_id": account["id"],
            "name": "Ourocard",
            "institution": "Banco do Brasil",
            "brand": "Elo",
            "last_digits": "61A9",
            "status": "active",
        },
    )
    assert invalid_digits.status_code == 422

    missing_account = client.post(
        "/cards",
        json={
            "name": "Ourocard",
            "institution": "Banco do Brasil",
            "brand": "Elo",
            "last_digits": "6149",
            "status": "active",
        },
    )
    assert missing_account.status_code == 200
    assert missing_account.json()["account_id"] is None
    assert client.delete(f"/cards/{missing_account.json()['id']}").status_code == 200

    invalid_account = client.post(
        "/cards",
        json={
            "account_id": "00000000-0000-4000-8000-000000000000",
            "name": "Ourocard",
            "institution": "Banco do Brasil",
            "brand": "Elo",
            "last_digits": "6149",
            "status": "active",
        },
    )
    assert invalid_account.status_code == 400

    created = client.post(
        "/cards",
        json={
            "account_id": account["id"],
            "name": "Ourocard",
            "institution": "Banco do Brasil",
            "brand": "Elo",
            "last_digits": "6149",
            "limit_amount": "5000.00",
            "closing_day": 20,
            "due_day": 7,
            "status": "active",
        },
    )
    assert created.status_code == 200
    card = created.json()
    assert card["last_digits"] == "6149"

    null_account = client.put(f"/cards/{card['id']}", json={"account_id": None})
    assert null_account.status_code == 200
    assert null_account.json()["account_id"] is None

    updated = client.put(f"/cards/{card['id']}", json={"brand": "Visa", "account_id": account["id"]})
    assert updated.status_code == 200
    assert updated.json()["brand"] == "Visa"
    assert updated.json()["account_id"] == account["id"]

    blocked_account_delete = client.delete(f"/accounts/{account['id']}")
    assert blocked_account_delete.status_code == 400
    assert blocked_account_delete.json()["error"]["message"] == "Não é possível inativar conta com cartões ativos vinculados."

    deleted = client.delete(f"/cards/{card['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "inactive"

    listed = client.get("/cards")
    assert listed.status_code == 200
    assert card["id"] not in {item["id"] for item in listed.json()}


def test_account_summary_includes_cards_statements_transactions_and_period_filters() -> None:
    client = TestClient(app)
    suffix = str(uuid4())[:8]
    user_id = settings.dev_user_id
    account = repository.create_account(
        user_id,
        {
            "name": f"Conta Summary {suffix}",
            "institution": "Banco do Brasil",
            "type": "checking",
            "balance": "1000.00",
            "status": "active",
        },
    )
    card = repository.create_card(
        user_id,
        {
            "account_id": account["id"],
            "name": f"Ourocard Summary {suffix}",
            "institution": "Banco do Brasil",
            "brand": "Elo",
            "last_digits": "6149",
            "limit_amount": "5000.00",
            "closing_day": 25,
            "due_day": 5,
            "status": "active",
        },
    )
    open_statement = repository.create_card_statement(
        {
            "user_id": user_id,
            "card_id": card["id"],
            "reference_month": "2026-05-01",
            "due_date": "2026-06-10",
            "closing_date": None,
            "total_amount": "120.00",
            "minimum_payment_amount": None,
            "status": "open",
            "paid_at": None,
            "source_file_id": None,
        }
    )
    paid_statement = repository.create_card_statement(
        {
            "user_id": user_id,
            "card_id": card["id"],
            "reference_month": "2026-04-01",
            "due_date": "2026-05-10",
            "closing_date": None,
            "total_amount": "80.00",
            "minimum_payment_amount": None,
            "status": "paid",
            "paid_at": "2026-05-10T12:00:00Z",
            "source_file_id": None,
        }
    )
    warning_statement = repository.create_card_statement(
        {
            "user_id": user_id,
            "card_id": card["id"],
            "reference_month": "2026-06-01",
            "due_date": "2026-07-10",
            "closing_date": None,
            "total_amount": "70.00",
            "minimum_payment_amount": None,
            "status": "open",
            "paid_at": None,
            "source_file_id": None,
        }
    )
    direct_income = repository.create_transaction(
        user_id,
        {
            "account_id": account["id"],
            "card_id": None,
            "card_statement_id": None,
            "transaction_date": "2026-05-02",
            "description": f"SALARIO {suffix}",
            "original_description": f"SALARIO {suffix}",
            "amount": "500.00",
            "type": "income",
            "category_id": None,
            "source_file_id": None,
            "installment_current": None,
            "installment_total": None,
            "status": "confirmed",
        },
    )
    card_expense = repository.create_transaction(
        user_id,
        {
            "account_id": None,
            "card_id": card["id"],
            "card_statement_id": open_statement["id"],
            "transaction_date": "2026-05-03",
            "description": f"COMPRA CARTAO {suffix}",
            "original_description": f"COMPRA CARTAO {suffix}",
            "amount": "50.00",
            "type": "expense",
            "category_id": None,
            "source_file_id": None,
            "installment_current": None,
            "installment_total": None,
            "status": "confirmed",
        },
    )
    repository.create_transaction(
        user_id,
        {
            "account_id": account["id"],
            "card_id": None,
            "card_statement_id": None,
            "transaction_date": "2026-04-01",
            "description": f"COMPRA ANTIGA {suffix}",
            "original_description": f"COMPRA ANTIGA {suffix}",
            "amount": "30.00",
            "type": "expense",
            "category_id": None,
            "source_file_id": None,
            "installment_current": None,
            "installment_total": None,
            "status": "confirmed",
        },
    )

    summary = client.get(
        f"/accounts/{account['id']}/summary",
        params={"start_date": "2026-05-01", "end_date": "2026-05-31"},
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["account"]["id"] == account["id"]
    assert body["cards"][0]["id"] == card["id"]
    assert body["cards"][0]["open_statement_count"] == 2
    assert body["cards"][0]["open_statement_total"] == "190.00"
    assert body["total_open_statements"] == "190.00"
    assert body["total_open_statements_ok"] == "120.00"
    assert body["total_open_statements_warning"] == "70.00"
    assert body["transaction_count"] == 2
    assert body["total_income"] == "500.00"
    assert body["total_expense"] == "50.00"
    assert body["net_balance_period"] == "450.00"
    assert {item["id"] for item in body["recent_transactions"]} == {direct_income["id"], card_expense["id"]}
    assert {item["id"] for item in body["open_statements"]} == {open_statement["id"], warning_statement["id"]}
    assert {item["integrity_status"] for item in body["open_statements"]} == {"difference", "no_transactions"}
    assert paid_statement["id"] not in {item["id"] for item in body["open_statements"]}

    missing = client.get(f"/accounts/{uuid4()}/summary")
    assert missing.status_code == 404


def test_card_summary_limits_statements_and_recent_transactions() -> None:
    client = TestClient(app)
    suffix = str(uuid4())[:8]
    user_id = settings.dev_user_id
    account = repository.create_account(
        user_id,
        {
            "name": f"Conta Cartao Summary {suffix}",
            "institution": "Banco do Brasil",
            "type": "checking",
            "balance": "1000.00",
            "status": "active",
        },
    )
    card = repository.create_card(
        user_id,
        {
            "account_id": account["id"],
            "name": f"Cartao Summary {suffix}",
            "institution": "Banco do Brasil",
            "brand": "Elo",
            "last_digits": "6149",
            "limit_amount": "1000.00",
            "closing_day": 25,
            "due_day": 5,
            "status": "active",
        },
    )
    open_statement = repository.create_card_statement(
        {
            "user_id": user_id,
            "card_id": card["id"],
            "reference_month": "2026-06-01",
            "due_date": "2026-07-05",
            "closing_date": None,
            "total_amount": "300.00",
            "minimum_payment_amount": None,
            "status": "open",
            "paid_at": None,
            "source_file_id": None,
        }
    )
    overdue_statement = repository.create_card_statement(
        {
            "user_id": user_id,
            "card_id": card["id"],
            "reference_month": "2026-05-01",
            "due_date": "2026-06-05",
            "closing_date": None,
            "total_amount": None,
            "minimum_payment_amount": None,
            "status": "overdue",
            "paid_at": None,
            "source_file_id": None,
        }
    )
    paid_statement = repository.create_card_statement(
        {
            "user_id": user_id,
            "card_id": card["id"],
            "reference_month": "2026-04-01",
            "due_date": "2026-05-05",
            "closing_date": None,
            "total_amount": "90.00",
            "minimum_payment_amount": None,
            "status": "paid",
            "paid_at": "2026-05-05T12:00:00Z",
            "source_file_id": None,
        }
    )
    repository.create_transaction(
        user_id,
        {
            "account_id": None,
            "card_id": card["id"],
            "card_statement_id": overdue_statement["id"],
            "transaction_date": "2026-05-03",
            "description": f"COMPRA ANTIGA {suffix}",
            "original_description": f"COMPRA ANTIGA {suffix}",
            "amount": "120.00",
            "type": "expense",
            "category_id": None,
            "source_file_id": None,
            "installment_current": None,
            "installment_total": None,
            "status": "confirmed",
        },
    )
    latest = repository.create_transaction(
        user_id,
        {
            "account_id": None,
            "card_id": card["id"],
            "card_statement_id": open_statement["id"],
            "transaction_date": "2026-06-03",
            "description": f"COMPRA RECENTE {suffix}",
            "original_description": f"COMPRA RECENTE {suffix}",
            "amount": "50.00",
            "type": "expense",
            "category_id": None,
            "source_file_id": None,
            "installment_current": None,
            "installment_total": None,
            "status": "confirmed",
        },
    )

    response = client.get(f"/cards/{card['id']}/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["card"]["id"] == card["id"]
    assert body["account"]["id"] == account["id"]
    assert body["limit_total"] == "1000.00"
    assert body["limit_used"] == "420.00"
    assert body["limit_available"] == "580.00"
    assert body["usage_percent"] == "42.00"
    assert [item["id"] for item in body["upcoming_statements"]] == [overdue_statement["id"], open_statement["id"]]
    assert [item["id"] for item in body["statement_history"][:3]] == [
        open_statement["id"],
        overdue_statement["id"],
        paid_statement["id"],
    ]
    assert body["recent_transactions"][0]["id"] == latest["id"]


def test_card_summary_without_limit_and_missing_card() -> None:
    client = TestClient(app)
    suffix = str(uuid4())[:8]
    user_id = settings.dev_user_id
    account = repository.create_account(
        user_id,
        {
            "name": f"Conta Sem Limite {suffix}",
            "institution": "Banco do Brasil",
            "type": "checking",
            "balance": "0",
            "status": "active",
        },
    )
    card = repository.create_card(
        user_id,
        {
            "account_id": account["id"],
            "name": f"Cartao Sem Limite {suffix}",
            "institution": "Banco do Brasil",
            "brand": "Visa",
            "last_digits": "1111",
            "limit_amount": None,
            "closing_day": None,
            "due_day": None,
            "status": "active",
        },
    )

    response = client.get(f"/cards/{card['id']}/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["limit_total"] is None
    assert body["limit_available"] is None
    assert body["usage_percent"] is None

    missing = client.get(f"/cards/{uuid4()}/summary")
    assert missing.status_code == 404

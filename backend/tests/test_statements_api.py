from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import repository
from app.core.config import settings
from app.main import app


def test_statements_summary_and_detail_totals() -> None:
    client = TestClient(app)
    suffix = str(uuid4())[:8]
    user_id = settings.dev_user_id
    account = repository.create_account(
        user_id,
        {
            "name": f"Conta Fatura {suffix}",
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
            "name": f"Ourocard {suffix}",
            "institution": "Banco do Brasil",
            "brand": "Elo",
            "last_digits": "6149",
            "limit_amount": "5000.00",
            "closing_day": 25,
            "due_day": 5,
            "status": "active",
        },
    )
    statement = repository.create_card_statement(
        {
            "user_id": user_id,
            "card_id": card["id"],
            "reference_month": "2026-05-01",
            "due_date": "2026-06-10",
            "closing_date": None,
            "total_amount": "120.00",
            "minimum_payment_amount": None,
            "status": "open",
            "source_file_id": None,
        }
    )
    repository.create_transaction(
        user_id,
        {
            "account_id": account["id"],
            "card_id": card["id"],
            "card_statement_id": statement["id"],
            "transaction_date": "2026-05-03",
            "description": f"COMPRA A {suffix}",
            "original_description": f"COMPRA A {suffix}",
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
            "card_id": card["id"],
            "card_statement_id": statement["id"],
            "transaction_date": "2026-05-04",
            "description": f"COMPRA B {suffix}",
            "original_description": f"COMPRA B {suffix}",
            "amount": "60.00",
            "type": "expense",
            "category_id": None,
            "source_file_id": None,
            "installment_current": None,
            "installment_total": None,
            "status": "confirmed",
        },
    )

    listed = client.get("/statements")
    assert listed.status_code == 200
    summary = next(item for item in listed.json() if item["id"] == statement["id"])
    assert summary["card_id"] == card["id"]
    assert summary["account_id"] == account["id"]
    assert summary["transaction_count"] == 2
    assert summary["reported_total"] == "120.00"
    assert summary["calculated_total"] == "110.00"
    assert summary["difference"] == "10.00"
    assert summary["integrity_status"] == "difference"
    assert summary["integrity_label"] == "Divergência"

    detail = client.get(f"/statements/{statement['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == statement["id"]
    assert len(body["transactions"]) == 2
    assert body["calculated_total"] == "110.00"

    paid = client.patch(f"/statements/{statement['id']}/status", json={"status": "paid"})
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"
    assert paid.json()["paid_at"] is not None

    reopened = client.patch(f"/statements/{statement['id']}/status", json={"status": "open"})
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "open"
    assert reopened.json()["paid_at"] is None

    missing = client.get(f"/statements/{uuid4()}")
    assert missing.status_code == 404


def test_statement_integrity_without_transactions() -> None:
    client = TestClient(app)
    suffix = str(uuid4())[:8]
    user_id = settings.dev_user_id
    account = repository.create_account(
        user_id,
        {
            "name": f"Conta Orfa {suffix}",
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
            "name": f"Ourocard Orfao {suffix}",
            "institution": "Banco do Brasil",
            "brand": "Elo",
            "last_digits": "1111",
            "limit_amount": "5000.00",
            "closing_day": 25,
            "due_day": 5,
            "status": "active",
        },
    )
    statement = repository.create_card_statement(
        {
            "user_id": user_id,
            "card_id": card["id"],
            "reference_month": "2026-05-01",
            "due_date": "2026-06-10",
            "closing_date": None,
            "total_amount": "120.00",
            "minimum_payment_amount": None,
            "status": "open",
            "source_file_id": None,
        }
    )

    detail = client.get(f"/statements/{statement['id']}")
    assert detail.status_code == 200
    assert detail.json()["transaction_count"] == 0
    assert detail.json()["integrity_status"] == "no_transactions"
    assert detail.json()["integrity_label"] == "Sem transações"


def test_delete_statement_only_without_transactions() -> None:
    client = TestClient(app)
    suffix = str(uuid4())[:8]
    user_id = settings.dev_user_id
    account = repository.create_account(
        user_id,
        {
            "name": f"Conta Delete Fatura {suffix}",
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
            "name": f"Ourocard Delete {suffix}",
            "institution": "Banco do Brasil",
            "brand": "Elo",
            "last_digits": "2222",
            "limit_amount": "5000.00",
            "closing_day": 25,
            "due_day": 5,
            "status": "active",
        },
    )
    orphan_statement = repository.create_card_statement(
        {
            "user_id": user_id,
            "card_id": card["id"],
            "reference_month": "2026-05-01",
            "due_date": "2026-06-10",
            "closing_date": None,
            "total_amount": "120.00",
            "minimum_payment_amount": None,
            "status": "open",
            "source_file_id": None,
        }
    )
    linked_statement = repository.create_card_statement(
        {
            "user_id": user_id,
            "card_id": card["id"],
            "reference_month": "2026-06-01",
            "due_date": "2026-07-10",
            "closing_date": None,
            "total_amount": "80.00",
            "minimum_payment_amount": None,
            "status": "open",
            "source_file_id": None,
        }
    )
    repository.create_transaction(
        user_id,
        {
            "account_id": account["id"],
            "card_id": card["id"],
            "card_statement_id": linked_statement["id"],
            "transaction_date": "2026-06-03",
            "description": f"COMPRA DELETE {suffix}",
            "original_description": f"COMPRA DELETE {suffix}",
            "amount": "50.00",
            "type": "expense",
            "category_id": None,
            "source_file_id": None,
            "installment_current": None,
            "installment_total": None,
            "status": "confirmed",
        },
    )

    blocked = client.delete(f"/statements/{linked_statement['id']}")
    assert blocked.status_code == 400
    assert blocked.json()["error"]["message"] == "Não é possível excluir fatura com transações vinculadas."

    deleted = client.delete(f"/statements/{orphan_statement['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"

    missing = client.get(f"/statements/{orphan_statement['id']}")
    assert missing.status_code == 404

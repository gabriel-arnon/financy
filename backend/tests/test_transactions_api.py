from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import repository
from app.core.config import settings
from app.main import app


def test_create_manual_transaction_persists_fields() -> None:
    client = TestClient(app)

    created = client.post(
        "/transactions",
        json={
            "transaction_date": "2026-06-10",
            "description": "TRANSACAO MANUAL",
            "original_description": "TRANSACAO MANUAL",
            "amount": "123.45",
            "type": "income",
            "status": "confirmed",
        },
    )

    assert created.status_code == 200
    transaction = created.json()
    assert transaction["transaction_date"] == "2026-06-10"
    assert transaction["description"] == "TRANSACAO MANUAL"
    assert transaction["original_description"] == "TRANSACAO MANUAL"
    assert transaction["amount"] == "123.45"
    assert transaction["type"] == "income"
    assert transaction["status"] == "confirmed"

    listed = client.get("/transactions")
    assert listed.status_code == 200
    assert transaction["id"] in {item["id"] for item in listed.json()}

    assert client.delete(f"/transactions/{transaction['id']}").status_code == 200


def test_delete_transaction_removes_it_from_listing() -> None:
    client = TestClient(app)
    created = client.post(
        "/transactions",
        json={
            "transaction_date": "2026-06-09",
            "description": "TRANSACAO PARA EXCLUIR",
            "amount": "42.00",
            "type": "expense",
            "status": "confirmed",
        },
    )
    assert created.status_code == 200
    transaction = created.json()

    deleted = client.delete(f"/transactions/{transaction['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"

    listed = client.get("/transactions")
    assert listed.status_code == 200
    assert transaction["id"] not in {item["id"] for item in listed.json()}

    deleted_again = client.delete(f"/transactions/{transaction['id']}")
    assert deleted_again.status_code == 404


def test_manual_card_transaction_attaches_statement_and_updates_card_summary() -> None:
    client = TestClient(app)
    suffix = str(uuid4())[:8]
    user_id = settings.dev_user_id
    account = repository.create_account(
        user_id,
        {
            "name": f"Conta Cartao Manual {suffix}",
            "institution": "Banco Teste",
            "type": "checking",
            "balance": "0",
            "status": "active",
        },
    )
    card = repository.create_card(
        user_id,
        {
            "account_id": account["id"],
            "name": f"Cartao Manual {suffix}",
            "institution": "Banco Teste",
            "brand": "Visa",
            "last_digits": "1234",
            "limit_amount": "1000.00",
            "closing_day": 20,
            "due_day": 10,
            "status": "active",
        },
    )

    created = client.post(
        "/transactions",
        json={
            "card_id": card["id"],
            "transaction_date": "2026-07-07",
            "description": "COMPRA MANUAL CARTAO",
            "amount": "89.90",
            "type": "expense",
            "status": "confirmed",
        },
    )

    assert created.status_code == 200
    transaction = created.json()
    assert transaction["card_id"] == card["id"]
    assert transaction["card_statement_id"]

    summary = client.get(f"/cards/{card['id']}/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["limit_used"] == "89.90"
    assert body["limit_available"] == "910.10"
    assert body["upcoming_statements"][0]["id"] == transaction["card_statement_id"]
    assert body["upcoming_statements"][0]["transaction_count"] == 1

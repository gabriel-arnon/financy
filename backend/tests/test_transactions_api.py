from fastapi.testclient import TestClient

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

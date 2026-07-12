from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import deps
from app.api import reimbursements as reimbursements_api
from app.core.config import settings
from app.main import app
from app.repositories.local_json import LocalJsonRepository


USER_ID = settings.dev_user_id
OTHER_USER_ID = "00000000-0000-4000-8000-000000000222"


def _client_with_repo(tmp_path: Path, monkeypatch) -> tuple[TestClient, LocalJsonRepository]:
    repo = LocalJsonRepository(tmp_path)
    monkeypatch.setattr(deps, "repository", repo)
    app.dependency_overrides.clear()
    return TestClient(app, raise_server_exceptions=False), repo


def _override_user(user_id: str) -> None:
    app.dependency_overrides[reimbursements_api.get_request_user_id] = lambda: user_id


def _seed_transaction(repo: LocalJsonRepository, user_id: str = USER_ID, amount: str = "100.00", tx_type: str = "expense") -> dict:
    account = repo.create_account(
        user_id,
        {
            "name": f"Conta Ressarcimento {str(uuid4())[:8]}",
            "institution": "Banco Teste",
            "type": "checking",
            "balance": "0",
            "status": "active",
        },
    )
    return repo.create_transaction(
        user_id,
        {
            "account_id": account["id"],
            "transaction_date": "2026-07-10",
            "description": "FARMACIA",
            "original_description": "FARMACIA ORIGINAL",
            "amount": amount,
            "type": tx_type,
            "status": "confirmed",
        },
    )


def _create_contact(client: TestClient, name: str = "Mae") -> dict:
    response = client.post("/reimbursements/contacts", json={"display_name": name, "email": "mae@example.com"})
    assert response.status_code == 200
    return response.json()


def _create_claim(client: TestClient, contact_id: str, title: str = "Julho") -> dict:
    response = client.post("/reimbursements/claims", json={"contact_id": contact_id, "title": title, "due_date": "2026-07-31"})
    assert response.status_code == 200
    return response.json()


def test_contact_crud_is_owner_scoped_and_soft_deletes(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)

    contact = _create_contact(client, "Mae")
    assert contact["owner_user_id"] == USER_ID
    assert contact["status"] == "active"
    assert client.post("/reimbursements/contacts", json={"display_name": " mae "}).status_code == 400

    renamed = client.patch(f"/reimbursements/contacts/{contact['id']}", json={"display_name": "Pai"})
    assert renamed.status_code == 200
    assert renamed.json()["display_name"] == "Pai"

    deleted = client.delete(f"/reimbursements/contacts/{contact['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "inactive"

    events = repo._read()["reimbursement_events"]
    assert [event["event_type"] for event in events] == ["contact_created", "contact_updated", "contact_updated"]


def test_claim_item_partial_amount_snapshot_and_send(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo, amount="187.50")
    contact = _create_contact(client)
    claim = _create_claim(client, contact["id"])

    added = client.post(
        f"/reimbursements/claims/{claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "87.50"},
    )
    assert added.status_code == 200
    body = added.json()
    assert body["total_amount"] == "87.50"
    assert body["items"][0]["transaction_snapshot"]["description"] == "FARMACIA"
    assert body["items"][0]["transaction_snapshot"]["account_id"] == transaction["account_id"]
    assert body["items"][0]["transaction_snapshot"]["amount_requested"] == "87.50"

    sent = client.post(f"/reimbursements/claims/{claim['id']}/send")
    assert sent.status_code == 200
    sent_body = sent.json()
    assert sent_body["status"] == "sent"
    assert sent_body["total_snapshot"] == "87.50"
    assert sent_body["total_amount"] == "87.50"

    events = [event["event_type"] for event in repo._read()["reimbursement_events"]]
    assert "claim_created" in events
    assert "item_added" in events
    assert "claim_sent" in events


def test_allocated_amount_cannot_exceed_transaction_amount_across_claims(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo, amount="100.00")
    contact = _create_contact(client)
    first_claim = _create_claim(client, contact["id"], "Primeira")
    second_claim = _create_claim(client, contact["id"], "Segunda")

    first = client.post(
        f"/reimbursements/claims/{first_claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "60.00"},
    )
    assert first.status_code == 200

    exceeded = client.post(
        f"/reimbursements/claims/{second_claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "41.00"},
    )
    assert exceeded.status_code == 400
    assert exceeded.json()["error"]["code"] == "reimbursement_amount_exceeds_transaction"

    allowed = client.post(
        f"/reimbursements/claims/{second_claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "40.00"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["total_amount"] == "40.00"


def test_reimbursement_item_update_and_remove_releases_allocation(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo, amount="100.00")
    contact = _create_contact(client)
    claim = _create_claim(client, contact["id"])
    other_claim = _create_claim(client, contact["id"], "Outra")

    added = client.post(
        f"/reimbursements/claims/{claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "80.00"},
    ).json()
    item_id = added["items"][0]["id"]

    updated = client.patch(f"/reimbursements/claims/{claim['id']}/items/{item_id}", json={"amount_requested": "50.00"})
    assert updated.status_code == 200
    assert updated.json()["total_amount"] == "50.00"

    blocked = client.post(
        f"/reimbursements/claims/{other_claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "51.00"},
    )
    assert blocked.status_code == 400

    removed = client.delete(f"/reimbursements/claims/{claim['id']}/items/{item_id}")
    assert removed.status_code == 200
    assert removed.json()["items"] == []

    available = client.post(
        f"/reimbursements/claims/{other_claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "100.00"},
    )
    assert available.status_code == 200


def test_sent_claim_cannot_be_edited_or_receive_items(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo)
    contact = _create_contact(client)
    claim = _create_claim(client, contact["id"])
    added = client.post(
        f"/reimbursements/claims/{claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "100.00"},
    ).json()
    item_id = added["items"][0]["id"]
    assert client.post(f"/reimbursements/claims/{claim['id']}/send").status_code == 200

    patch_claim = client.patch(f"/reimbursements/claims/{claim['id']}", json={"title": "Novo titulo"})
    assert patch_claim.status_code == 400
    assert patch_claim.json()["error"]["code"] == "reimbursement_claim_not_draft"

    patch_item = client.patch(f"/reimbursements/claims/{claim['id']}/items/{item_id}", json={"amount_requested": "90.00"})
    assert patch_item.status_code == 400
    assert patch_item.json()["error"]["code"] == "reimbursement_claim_not_draft"

    remove_item = client.delete(f"/reimbursements/claims/{claim['id']}/items/{item_id}")
    assert remove_item.status_code == 400
    assert remove_item.json()["error"]["code"] == "reimbursement_claim_not_draft"

    another_transaction = _seed_transaction(repo, amount="10.00")
    add_item = client.post(
        f"/reimbursements/claims/{claim['id']}/items",
        json={"transaction_id": another_transaction["id"], "amount_requested": "10.00"},
    )
    assert add_item.status_code == 400
    assert add_item.json()["error"]["code"] == "reimbursement_claim_not_draft"


def test_only_owner_transactions_can_be_added(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    contact = _create_contact(client)
    claim = _create_claim(client, contact["id"])
    other_transaction = _seed_transaction(repo, user_id=OTHER_USER_ID, amount="50.00")

    response = client.post(
        f"/reimbursements/claims/{claim['id']}/items",
        json={"transaction_id": other_transaction["id"], "amount_requested": "50.00"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "transaction_not_found"


def test_other_owner_cannot_access_claim_or_attach_own_transaction_to_it(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    contact = _create_contact(client)
    claim = _create_claim(client, contact["id"])

    _override_user(OTHER_USER_ID)
    other_transaction = _seed_transaction(repo, user_id=OTHER_USER_ID, amount="30.00")

    assert client.get(f"/reimbursements/claims/{claim['id']}").status_code == 404
    response = client.post(
        f"/reimbursements/claims/{claim['id']}/items",
        json={"transaction_id": other_transaction["id"], "amount_requested": "30.00"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "reimbursement_claim_not_found"
    app.dependency_overrides.clear()


def test_non_expense_transaction_is_not_reimbursable(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo, amount="100.00", tx_type="income")
    contact = _create_contact(client)
    claim = _create_claim(client, contact["id"])

    response = client.post(
        f"/reimbursements/claims/{claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "50.00"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "transaction_not_reimbursable"


def test_cancel_claim_sets_terminal_status(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client_with_repo(tmp_path, monkeypatch)
    contact = _create_contact(client)
    claim = _create_claim(client, contact["id"])

    canceled = client.post(f"/reimbursements/claims/{claim['id']}/cancel")

    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"
    assert client.post(f"/reimbursements/claims/{claim['id']}/cancel").status_code == 400


def test_concurrent_item_creation_cannot_over_allocate_transaction(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo, amount="100.00")
    contact = _create_contact(client)
    first_claim = _create_claim(client, contact["id"], "Primeira")
    second_claim = _create_claim(client, contact["id"], "Segunda")

    def add_item(claim_id: str):
        return client.post(
            f"/reimbursements/claims/{claim_id}/items",
            json={"transaction_id": transaction["id"], "amount_requested": "60.00"},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(add_item, [first_claim["id"], second_claim["id"]]))

    statuses = sorted(response.status_code for response in responses)
    assert statuses == [200, 400]
    allocated = sum(float(item["amount_requested"]) for item in repo.list_reimbursement_items_by_transaction(USER_ID, transaction["id"]))
    assert allocated == 60.0


def test_concurrent_item_update_cannot_over_allocate_transaction(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo, amount="100.00")
    contact = _create_contact(client)
    first_claim = _create_claim(client, contact["id"], "Primeira")
    second_claim = _create_claim(client, contact["id"], "Segunda")
    first_item = client.post(
        f"/reimbursements/claims/{first_claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "40.00"},
    ).json()["items"][0]
    second_item = client.post(
        f"/reimbursements/claims/{second_claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "40.00"},
    ).json()["items"][0]

    def update_item(args):
        claim_id, item_id = args
        return client.patch(f"/reimbursements/claims/{claim_id}/items/{item_id}", json={"amount_requested": "60.00"})

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(update_item, [(first_claim["id"], first_item["id"]), (second_claim["id"], second_item["id"])]))

    statuses = sorted(response.status_code for response in responses)
    assert statuses == [200, 400]
    allocated = sum(float(item["amount_requested"]) for item in repo.list_reimbursement_items_by_transaction(USER_ID, transaction["id"]))
    assert allocated <= 100.0


def test_canceling_claim_releases_allocated_balance_but_keeps_history(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo, amount="100.00")
    contact = _create_contact(client)
    claim = _create_claim(client, contact["id"])
    next_claim = _create_claim(client, contact["id"], "Depois")
    client.post(
        f"/reimbursements/claims/{claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "100.00"},
    )

    canceled = client.post(f"/reimbursements/claims/{claim['id']}/cancel")
    assert canceled.status_code == 200
    canceled_body = canceled.json()
    assert canceled_body["status"] == "canceled"
    assert canceled_body["items"][0]["status"] == "canceled"
    assert repo.list_reimbursement_items_by_transaction(USER_ID, transaction["id"]) == []

    added_again = client.post(
        f"/reimbursements/claims/{next_claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "100.00"},
    )
    assert added_again.status_code == 200


def test_snapshot_refreshes_before_send_and_remains_immutable_after_send(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo, amount="100.00")
    contact = _create_contact(client)
    claim = _create_claim(client, contact["id"])
    added = client.post(
        f"/reimbursements/claims/{claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "100.00"},
    ).json()
    assert added["items"][0]["transaction_snapshot"]["description"] == "FARMACIA"

    repo.update_transaction(USER_ID, transaction["id"], {"description": "FARMACIA ALTERADA", "amount": "120.00"})
    refreshed = client.post(f"/reimbursements/claims/{claim['id']}/refresh-snapshots")
    assert refreshed.status_code == 200
    assert refreshed.json()["items"][0]["transaction_snapshot"]["description"] == "FARMACIA ALTERADA"

    sent = client.post(f"/reimbursements/claims/{claim['id']}/send")
    assert sent.status_code == 200
    sent_snapshot = sent.json()["items"][0]["transaction_snapshot"]
    assert sent_snapshot["description"] == "FARMACIA ALTERADA"
    assert sent_snapshot["finalized_at"] is not None

    repo.update_transaction(USER_ID, transaction["id"], {"description": "ALTERADA DEPOIS DO ENVIO"})
    detail = client.get(f"/reimbursements/claims/{claim['id']}")
    assert detail.status_code == 200
    assert detail.json()["items"][0]["transaction_snapshot"]["description"] == "FARMACIA ALTERADA"
    assert detail.json()["items"][0]["snapshot_is_current"] is False


def test_send_fails_when_transaction_becomes_ineligible_or_overallocated(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo, amount="100.00")
    contact = _create_contact(client)
    claim = _create_claim(client, contact["id"])
    client.post(
        f"/reimbursements/claims/{claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "100.00"},
    )
    repo.update_transaction(USER_ID, transaction["id"], {"type": "income"})

    ineligible = client.post(f"/reimbursements/claims/{claim['id']}/send")
    assert ineligible.status_code == 400
    assert ineligible.json()["error"]["code"] == "transaction_not_reimbursable"

    repo.update_transaction(USER_ID, transaction["id"], {"type": "expense", "amount": "80.00"})
    overallocated = client.post(f"/reimbursements/claims/{claim['id']}/send")
    assert overallocated.status_code == 400
    assert overallocated.json()["error"]["code"] == "reimbursement_amount_exceeds_transaction"


def test_overview_eligible_transactions_timeline_and_owner_user_id_payload(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo, amount="75.00")

    contact_response = client.post(
        "/reimbursements/contacts",
        json={"display_name": "Empresa", "owner_user_id": OTHER_USER_ID},
    )
    assert contact_response.status_code == 200
    contact = contact_response.json()
    assert contact["owner_user_id"] == USER_ID

    claim = _create_claim(client, contact["id"], "Reembolso")
    client.post(
        f"/reimbursements/claims/{claim['id']}/items",
        json={"transaction_id": transaction["id"], "amount_requested": "25.00", "owner_user_id": OTHER_USER_ID},
    )

    overview = client.get("/reimbursements/overview")
    assert overview.status_code == 200
    assert overview.json()["draft_count"] == 1

    eligible = client.get("/reimbursements/eligible-transactions?q=FARMACIA&limit=10")
    assert eligible.status_code == 200
    body = eligible.json()
    assert body[0]["id"] == transaction["id"]
    assert body[0]["allocated_amount"] == "25.00"
    assert body[0]["available_amount"] == "50.00"

    events = client.get(f"/reimbursements/claims/{claim['id']}/events")
    assert events.status_code == 200
    event_types = [event["event_type"] for event in events.json()]
    assert "claim_created" in event_types
    assert "item_added" in event_types

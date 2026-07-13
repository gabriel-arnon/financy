from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import deps
from app.api import reimbursements as reimbursements_api
from app.core.auth import CurrentUser
from app.core.config import settings
from app.main import app
from app.repositories.local_json import LocalJsonRepository


USER_ID = settings.dev_user_id
OTHER_USER_ID = "00000000-0000-4000-8000-000000000222"
GUEST_USER_ID = "00000000-0000-4000-8000-000000000333"


def _client_with_repo(tmp_path: Path, monkeypatch) -> tuple[TestClient, LocalJsonRepository]:
    repo = LocalJsonRepository(tmp_path)
    monkeypatch.setattr(deps, "repository", repo)
    app.dependency_overrides.clear()
    return TestClient(app, raise_server_exceptions=False), repo


def _override_user(user_id: str) -> None:
    app.dependency_overrides[reimbursements_api.get_request_user_id] = lambda: user_id


def _override_current_user(user_id: str, email: str) -> None:
    user = CurrentUser(id=user_id, email=email, full_name="Guest User", auth_source="test")
    app.dependency_overrides[reimbursements_api.get_request_user] = lambda: user


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


def test_invitation_acceptance_creates_guest_membership_and_limits_claims(tmp_path: Path, monkeypatch) -> None:
    client, _repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(_repo, amount="100.00")
    contact = _create_contact(client)
    claim = _create_claim(client, contact["id"], "Julho")
    assert client.post(f"/reimbursements/claims/{claim['id']}/items", json={"transaction_id": transaction["id"], "amount_requested": "100.00"}).status_code == 200
    sent = client.post(f"/reimbursements/claims/{claim['id']}/send").json()

    invite = client.post("/reimbursements/invitations", json={"contact_id": contact["id"], "claim_id": claim["id"]})
    assert invite.status_code == 200
    token = invite.json()["accept_token"]
    assert "token_hash" not in invite.json()

    _override_current_user(GUEST_USER_ID, "mae@example.com")
    accepted = client.post("/reimbursements/guest/invitations/accept", json={"token": token})
    assert accepted.status_code == 200
    assert accepted.json()["contact_id"] == contact["id"]

    guest_claims = client.get("/reimbursements/guest/claims")
    assert guest_claims.status_code == 200
    assert [item["id"] for item in guest_claims.json()] == [sent["id"]]
    guest_payload = guest_claims.json()[0]
    assert "owner_user_id" not in guest_payload
    assert "contact" not in guest_payload
    assert "transaction_id" not in guest_payload["items"][0]
    assert "transaction_snapshot" not in guest_payload["items"][0]

    _override_user(USER_ID)
    other_claim = _create_claim(client, contact["id"], "Rascunho invisivel")
    _override_current_user(GUEST_USER_ID, "mae@example.com")
    hidden = client.get(f"/reimbursements/guest/claims/{other_claim['id']}")
    assert hidden.status_code == 404


def test_guest_invitation_rejects_wrong_email_and_revoked_access(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo, amount="80.00")
    contact = _create_contact(client)
    claim = _create_claim(client, contact["id"])
    assert client.post(f"/reimbursements/claims/{claim['id']}/items", json={"transaction_id": transaction["id"], "amount_requested": "80.00"}).status_code == 200
    assert client.post(f"/reimbursements/claims/{claim['id']}/send").status_code == 200
    invite = client.post("/reimbursements/invitations", json={"contact_id": contact["id"], "claim_id": claim["id"]}).json()

    _override_current_user(GUEST_USER_ID, "outra@example.com")
    wrong = client.post("/reimbursements/guest/invitations/accept", json={"token": invite["accept_token"]})
    assert wrong.status_code == 404

    _override_current_user(GUEST_USER_ID, "mae@example.com")
    accepted = client.post("/reimbursements/guest/invitations/accept", json={"token": invite["accept_token"]})
    assert accepted.status_code == 200
    membership_id = accepted.json()["id"]

    _override_user(USER_ID)
    revoked = client.post(f"/reimbursements/memberships/{membership_id}/revoke")
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    _override_current_user(GUEST_USER_ID, "mae@example.com")
    assert client.get("/reimbursements/guest/claims").json() == []


def test_guest_acknowledges_and_disputes_shared_claim(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo, amount="60.00")
    contact = _create_contact(client)
    claim = _create_claim(client, contact["id"])
    assert client.post(f"/reimbursements/claims/{claim['id']}/items", json={"transaction_id": transaction["id"], "amount_requested": "60.00"}).status_code == 200
    assert client.post(f"/reimbursements/claims/{claim['id']}/send").status_code == 200
    invite = client.post("/reimbursements/invitations", json={"contact_id": contact["id"], "claim_id": claim["id"]}).json()
    _override_current_user(GUEST_USER_ID, "mae@example.com")
    assert client.post("/reimbursements/guest/invitations/accept", json={"token": invite["accept_token"]}).status_code == 200

    acknowledged = client.post(f"/reimbursements/guest/claims/{claim['id']}/acknowledge")
    assert acknowledged.status_code == 200
    assert acknowledged.json()["status"] == "acknowledged"
    assert client.post(f"/reimbursements/guest/claims/{claim['id']}/acknowledge").status_code == 200

    missing_note = client.post(f"/reimbursements/guest/claims/{claim['id']}/dispute", json={"note": ""})
    assert missing_note.status_code == 400
    assert missing_note.json()["error"]["code"] == "reimbursement_dispute_note_required"

    disputed = client.post(f"/reimbursements/guest/claims/{claim['id']}/dispute", json={"note": "Tenho duvida."})
    assert disputed.status_code == 200
    assert disputed.json()["status"] == "disputed"
    event_types = [event["event_type"] for event in repo._read()["reimbursement_events"]]
    assert "claim_acknowledged" in event_types
    assert "claim_disputed" in event_types


def test_guest_claim_attachments_are_explicit_and_revocable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "private_files_backend", "local")
    monkeypatch.setattr(settings, "upload_dir", tmp_path)
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo, amount="45.00")
    contact = _create_contact(client)
    claim = _create_claim(client, contact["id"])
    assert client.post(f"/reimbursements/claims/{claim['id']}/items", json={"transaction_id": transaction["id"], "amount_requested": "45.00"}).status_code == 200
    assert client.post(f"/reimbursements/claims/{claim['id']}/send").status_code == 200
    shared_file = repo.create_stored_file(
        USER_ID,
        {
            "storage_bucket": "private",
            "storage_path": "user/file-a.pdf",
            "original_filename": "recibo.pdf",
            "declared_mime_type": "application/pdf",
            "detected_mime_type": "application/pdf",
            "size_bytes": 20,
            "sha256_hash": "hash-a",
            "source": "manual",
            "status": "available",
            "scan_status": "skipped",
            "metadata": {},
        },
    )
    local_object = settings.upload_dir / "private_files" / shared_file["storage_path"]
    local_object.parent.mkdir(parents=True, exist_ok=True)
    local_object.write_bytes(b"%PDF-1.4\n%test\n")
    unshared_file = repo.create_stored_file(
        USER_ID,
        {
            "storage_bucket": "private",
            "storage_path": "user/file-b.pdf",
            "original_filename": "privado.pdf",
            "declared_mime_type": "application/pdf",
            "detected_mime_type": "application/pdf",
            "size_bytes": 20,
            "sha256_hash": "hash-b",
            "source": "manual",
            "status": "available",
            "scan_status": "skipped",
            "metadata": {},
        },
    )
    attached = client.post(f"/reimbursements/claims/{claim['id']}/attachments", json={"file_id": shared_file["id"]})
    assert attached.status_code == 200
    attachment_id = attached.json()["id"]
    assert "storage_path" not in attached.json()["file"]

    invite = client.post("/reimbursements/invitations", json={"contact_id": contact["id"], "claim_id": claim["id"]}).json()
    _override_current_user(GUEST_USER_ID, "mae@example.com")
    membership = client.post("/reimbursements/guest/invitations/accept", json={"token": invite["accept_token"]}).json()

    attachments = client.get(f"/reimbursements/guest/claims/{claim['id']}/attachments")
    assert attachments.status_code == 200
    assert [item["id"] for item in attachments.json()] == [attachment_id]
    assert "storage_path" not in attachments.json()[0]["file"]
    signed = client.get(f"/reimbursements/guest/claims/{claim['id']}/attachments/{attachment_id}/signed-url")
    assert signed.status_code == 200

    blocked_unshared = client.get(f"/reimbursements/guest/claims/{claim['id']}/attachments/{unshared_file['id']}/signed-url")
    assert blocked_unshared.status_code == 404

    _override_user(USER_ID)
    assert client.post(f"/reimbursements/memberships/{membership['id']}/revoke").status_code == 200
    _override_current_user(GUEST_USER_ID, "mae@example.com")
    assert client.get(f"/reimbursements/guest/claims/{claim['id']}/attachments").status_code == 404

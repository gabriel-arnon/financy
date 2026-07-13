from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.repositories.postgres import PostgresRepository
from app.schemas.reimbursements import (
    ReimbursementClaimCreate,
    ReimbursementCommentCreate,
    ReimbursementInvitationAccept,
    ReimbursementInvitationCreate,
    ReimbursementClaimUpdate,
    ReimbursementContactCreate,
    ReimbursementContactUpdate,
    ReimbursementItemCreate,
    ReimbursementItemUpdate,
)
from app.services.reimbursement_service import ReimbursementService
from scripts.apply_migrations import apply_migrations
from scripts.dev_db_safety import assert_local_database_url
from scripts.prepare_test_database import ensure_database


pytestmark = pytest.mark.postgres

USER_ID = "00000000-0000-4000-8000-00000000a001"
GUEST_ID = "00000000-0000-4000-8000-00000000a003"
OTHER_GUEST_ID = "00000000-0000-4000-8000-00000000a004"


@pytest.fixture()
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        raise RuntimeError("TEST_DATABASE_URL is required for PostgreSQL integration tests.")
    assert_local_database_url(url, purpose="postgres integration tests")
    ensure_database(url)
    apply_migrations(url, reset=True)
    return url


@pytest.fixture()
def repo(database_url: str):
    repository = PostgresRepository(database_url, dev_user_id=USER_ID)
    try:
        yield repository
    finally:
        repository.pool.close()


def _service(repository: PostgresRepository) -> ReimbursementService:
    return ReimbursementService(repository)


def _seed_transaction(repository: PostgresRepository, *, amount: str = "100.00", tx_type: str = "expense", description: str = "FARMACIA") -> dict:
    account = repository.create_account(
        USER_ID,
        {
            "name": f"Conta PG {uuid4()}",
            "institution": "Banco Dev",
            "type": "checking",
            "balance": "0",
            "status": "active",
        },
    )
    return repository.create_transaction(
        USER_ID,
        {
            "account_id": account["id"],
            "transaction_date": "2026-07-10",
            "description": description,
            "original_description": description,
            "amount": amount,
            "type": tx_type,
            "status": "confirmed",
        },
    )


def _create_claim(service: ReimbursementService, title: str = "Julho") -> str:
    contact = service.create_contact(USER_ID, ReimbursementContactCreate(display_name=f"Pessoa {uuid4()}"))
    claim = service.create_claim(USER_ID, ReimbursementClaimCreate(contact_id=contact.id, title=title, due_date="2026-07-31"))
    return claim.id


def _add_item(service: ReimbursementService, claim_id: str, transaction_id: str, amount: str):
    return service.add_item(USER_ID, claim_id, ReimbursementItemCreate(transaction_id=transaction_id, amount_requested=Decimal(amount)))


def _guest(user_id: str = GUEST_ID, email: str = "mae@example.com"):
    return SimpleNamespace(id=user_id, email=email, full_name="Guest", auth_source="test")


def _sent_claim_with_contact(repository: PostgresRepository, *, email: str = "mae@example.com") -> tuple[ReimbursementService, dict, str]:
    service = _service(repository)
    transaction = _seed_transaction(repository, amount="100.00")
    contact = service.create_contact(USER_ID, ReimbursementContactCreate(display_name=f"Mae {uuid4()}", email=email))
    claim = service.create_claim(USER_ID, ReimbursementClaimCreate(contact_id=contact.id, title="Julho"))
    _add_item(service, claim.id, transaction["id"], "100.00")
    service.send_claim(USER_ID, claim.id)
    return service, {"id": contact.id, "email": email}, claim.id


def _total_allocated(repository: PostgresRepository, transaction_id: str) -> Decimal:
    with repository._connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            select coalesce(sum(ri.amount_requested), 0) as total_allocated
            from reimbursement_items ri
            join reimbursement_claims rc on rc.id = ri.claim_id
            where ri.owner_user_id = %s
              and ri.transaction_id = %s
              and ri.status = 'active'
              and rc.status <> 'canceled'
            """,
            (USER_ID, transaction_id),
        )
        return Decimal(str(cur.fetchone()["total_allocated"])).quantize(Decimal("0.01"))


def _run_concurrently(functions):
    barrier = threading.Barrier(len(functions))

    def run(fn):
        barrier.wait(timeout=10)
        try:
            return ("ok", fn())
        except AppError as exc:
            return ("error", exc.code)

    with ThreadPoolExecutor(max_workers=len(functions)) as executor:
        return [future.result() for future in [executor.submit(run, fn) for fn in functions]]


def test_owner_only_flow_uses_real_postgres_repository(repo: PostgresRepository) -> None:
    service = _service(repo)
    transaction = _seed_transaction(repo, amount="300.00")
    contact = service.create_contact(USER_ID, ReimbursementContactCreate(display_name="Mae", email="mae@example.com"))
    edited = service.update_contact(USER_ID, contact.id, ReimbursementContactUpdate(display_name="Mae Editada"))
    assert edited.display_name == "Mae Editada"
    inactive = service.delete_contact(USER_ID, contact.id)
    assert inactive.status.value == "inactive"

    active_contact = service.create_contact(USER_ID, ReimbursementContactCreate(display_name="Pai"))
    claim = service.create_claim(USER_ID, ReimbursementClaimCreate(contact_id=active_contact.id, title="Julho"))
    with_item = _add_item(service, claim.id, transaction["id"], "100.00")
    item_id = with_item.items[0].id
    updated = service.update_item(USER_ID, claim.id, item_id, ReimbursementItemUpdate(amount_requested=Decimal("150.00")))
    assert updated.total_amount == Decimal("150.00")

    repo.update_transaction(USER_ID, transaction["id"], {"description": "FARMACIA EDITADA"})
    refreshed = service.refresh_claim_snapshots(USER_ID, claim.id)
    assert refreshed.items[0].transaction_snapshot["description"] == "FARMACIA EDITADA"

    sent = service.send_claim(USER_ID, claim.id)
    assert sent.status.value == "sent"
    assert sent.total_snapshot == Decimal("150.00")
    with pytest.raises(AppError) as edit_error:
        service.update_claim(USER_ID, claim.id, ReimbursementClaimUpdate(title="Bloqueado"))
    assert edit_error.value.code == "reimbursement_claim_not_draft"

    canceled = service.cancel_claim(USER_ID, claim.id)
    assert canceled.status.value == "canceled"
    assert _total_allocated(repo, transaction["id"]) == Decimal("0.00")
    events = [event.event_type for event in service.list_events(USER_ID, claim.id)]
    assert "claim_created" in events
    assert "item_added" in events
    assert "claim_snapshots_refreshed" in events
    assert "claim_sent" in events
    assert "claim_canceled" in events


def test_concurrent_adds_on_two_claims_do_not_overallocate(database_url: str, repo: PostgresRepository) -> None:
    transaction = _seed_transaction(repo, amount="100.00")
    claim_a = _create_claim(_service(repo), "A")
    claim_b = _create_claim(_service(repo), "B")

    def add_to(claim_id: str):
        isolated_repo = PostgresRepository(database_url, dev_user_id=USER_ID)
        try:
            return _add_item(_service(isolated_repo), claim_id, transaction["id"], "70.00")
        finally:
            isolated_repo.pool.close()

    results = _run_concurrently([lambda: add_to(claim_a), lambda: add_to(claim_b)])
    assert sorted(result[0] for result in results) == ["error", "ok"]
    assert [result[1] for result in results if result[0] == "error"] == ["reimbursement_amount_exceeds_transaction"]
    assert _total_allocated(repo, transaction["id"]) <= Decimal("100.00")


def test_concurrent_updates_do_not_overallocate(database_url: str, repo: PostgresRepository) -> None:
    service = _service(repo)
    transaction = _seed_transaction(repo, amount="100.00")
    claim_a = _create_claim(service, "A")
    claim_b = _create_claim(service, "B")
    item_a = _add_item(service, claim_a, transaction["id"], "30.00").items[0]
    item_b = _add_item(service, claim_b, transaction["id"], "30.00").items[0]

    def update_item(claim_id: str, item_id: str):
        isolated_repo = PostgresRepository(database_url, dev_user_id=USER_ID)
        try:
            return _service(isolated_repo).update_item(USER_ID, claim_id, item_id, ReimbursementItemUpdate(amount_requested=Decimal("70.00")))
        finally:
            isolated_repo.pool.close()

    results = _run_concurrently([lambda: update_item(claim_a, item_a.id), lambda: update_item(claim_b, item_b.id)])
    assert sorted(result[0] for result in results) == ["error", "ok"]
    assert [result[1] for result in results if result[0] == "error"] == ["reimbursement_amount_exceeds_transaction"]
    assert _total_allocated(repo, transaction["id"]) <= Decimal("100.00")


def test_cancel_concurrent_with_add_keeps_allocation_consistent(database_url: str, repo: PostgresRepository) -> None:
    service = _service(repo)
    transaction = _seed_transaction(repo, amount="100.00")
    claim_a = _create_claim(service, "A")
    claim_b = _create_claim(service, "B")
    _add_item(service, claim_a, transaction["id"], "70.00")

    def cancel_claim():
        isolated_repo = PostgresRepository(database_url, dev_user_id=USER_ID)
        try:
            return _service(isolated_repo).cancel_claim(USER_ID, claim_a)
        finally:
            isolated_repo.pool.close()

    def add_after_or_during_cancel():
        isolated_repo = PostgresRepository(database_url, dev_user_id=USER_ID)
        try:
            return _add_item(_service(isolated_repo), claim_b, transaction["id"], "70.00")
        finally:
            isolated_repo.pool.close()

    results = _run_concurrently([cancel_claim, add_after_or_during_cancel])
    assert any(result[0] == "ok" for result in results)
    assert _total_allocated(repo, transaction["id"]) <= Decimal("100.00")


def test_retry_draft_reservation_and_canceled_release(repo: PostgresRepository) -> None:
    service = _service(repo)
    transaction = _seed_transaction(repo, amount="100.00")
    claim_a = _create_claim(service, "A")
    claim_b = _create_claim(service, "B")

    _add_item(service, claim_a, transaction["id"], "100.00")
    with pytest.raises(AppError) as retry_error:
        _add_item(service, claim_a, transaction["id"], "100.00")
    assert retry_error.value.code == "reimbursement_item_duplicate"
    with pytest.raises(AppError) as blocked_error:
        _add_item(service, claim_b, transaction["id"], "1.00")
    assert blocked_error.value.code == "reimbursement_amount_exceeds_transaction"

    service.cancel_claim(USER_ID, claim_a)
    _add_item(service, claim_b, transaction["id"], "100.00")
    assert _total_allocated(repo, transaction["id"]) == Decimal("100.00")


def test_invitation_token_hash_guest_payload_and_revocation(repo: PostgresRepository) -> None:
    service, contact, claim_id = _sent_claim_with_contact(repo)
    invitation = service.create_invitation(
        USER_ID,
        ReimbursementInvitationCreate(contact_id=contact["id"], claim_id=claim_id, expires_in_days=14),
    )
    stored = repo.get_reimbursement_invitation(USER_ID, invitation.id)
    assert stored is not None
    assert stored["token_hash"] != invitation.accept_token
    assert len(stored["token_hash"]) == 64

    with pytest.raises(AppError) as wrong_email:
        service.accept_invitation(_guest(email="outra@example.com"), ReimbursementInvitationAccept(token=invitation.accept_token))
    assert wrong_email.value.code == "reimbursement_invitation_invalid"

    membership = service.accept_invitation(_guest(), ReimbursementInvitationAccept(token=invitation.accept_token))
    assert membership.status.value == "active"
    duplicate = service.accept_invitation(_guest(), ReimbursementInvitationAccept(token=invitation.accept_token))
    assert duplicate.id == membership.id

    guest_claim = service.get_guest_claim(GUEST_ID, claim_id)
    body = guest_claim.model_dump(mode="json")
    assert "owner_user_id" not in body
    assert "contact_id" not in body
    assert "transaction_id" not in body["items"][0]
    assert "account_id" not in body["items"][0]
    assert "source_signature" not in body["items"][0]

    service.revoke_membership(USER_ID, membership.id)
    assert service.list_guest_claims(GUEST_ID) == []
    with pytest.raises(AppError) as revoked_access:
        service.get_guest_claim(GUEST_ID, claim_id)
    assert revoked_access.value.code == "reimbursement_claim_not_found"


def test_expired_and_revoked_invitations_are_rejected(repo: PostgresRepository) -> None:
    service, contact, claim_id = _sent_claim_with_contact(repo)
    expired = service.create_invitation(
        USER_ID,
        ReimbursementInvitationCreate(contact_id=contact["id"], claim_id=claim_id, expires_in_days=1),
    )
    repo.update_reimbursement_invitation(USER_ID, expired.id, {"expires_at": "2026-01-01T00:00:00+00:00"})
    with pytest.raises(AppError) as expired_error:
        service.accept_invitation(_guest(), ReimbursementInvitationAccept(token=expired.accept_token))
    assert expired_error.value.code == "reimbursement_invitation_invalid"

    active = service.create_invitation(
        USER_ID,
        ReimbursementInvitationCreate(contact_id=contact["id"], claim_id=claim_id, expires_in_days=14),
    )
    service.revoke_invitation(USER_ID, active.id)
    with pytest.raises(AppError) as revoked_error:
        service.accept_invitation(_guest(), ReimbursementInvitationAccept(token=active.accept_token))
    assert revoked_error.value.code == "reimbursement_invitation_invalid"


def test_concurrent_invitation_accept_creates_single_membership(database_url: str, repo: PostgresRepository) -> None:
    service, contact, claim_id = _sent_claim_with_contact(repo)
    invitation = service.create_invitation(
        USER_ID,
        ReimbursementInvitationCreate(contact_id=contact["id"], claim_id=claim_id, expires_in_days=14),
    )

    def accept_token():
        isolated_repo = PostgresRepository(database_url, dev_user_id=USER_ID)
        try:
            return _service(isolated_repo).accept_invitation(_guest(), ReimbursementInvitationAccept(token=invitation.accept_token))
        finally:
            isolated_repo.pool.close()

    results = _run_concurrently([accept_token, accept_token])
    assert [result[0] for result in results] == ["ok", "ok"]
    memberships = repo.list_reimbursement_memberships(USER_ID)
    active = [item for item in memberships if item["contact_id"] == contact["id"] and item["auth_user_id"] == GUEST_ID and item["status"] == "active"]
    assert len(active) == 1


def test_same_guest_can_accept_different_owners(repo: PostgresRepository) -> None:
    service, contact, claim_id = _sent_claim_with_contact(repo)
    invitation = service.create_invitation(USER_ID, ReimbursementInvitationCreate(contact_id=contact["id"], claim_id=claim_id))
    first = service.accept_invitation(_guest(), ReimbursementInvitationAccept(token=invitation.accept_token))

    other_owner = "00000000-0000-4000-8000-00000000b001"
    repo.ensure_profile(other_owner, email="owner-b@example.com")
    transaction = _seed_transaction(repo, amount="50.00")
    repo.update_transaction(USER_ID, transaction["id"], {"user_id": other_owner})
    other_service = _service(repo)
    other_contact = other_service.create_contact(other_owner, ReimbursementContactCreate(display_name="Mae B", email="mae@example.com"))
    other_claim = other_service.create_claim(other_owner, ReimbursementClaimCreate(contact_id=other_contact.id, title="Agosto"))
    other_service.add_item(other_owner, other_claim.id, ReimbursementItemCreate(transaction_id=transaction["id"], amount_requested=Decimal("50.00")))
    other_service.send_claim(other_owner, other_claim.id)
    second_invitation = other_service.create_invitation(other_owner, ReimbursementInvitationCreate(contact_id=other_contact.id, claim_id=other_claim.id))
    second = other_service.accept_invitation(_guest(), ReimbursementInvitationAccept(token=second_invitation.accept_token))

    assert first.owner_user_id != second.owner_user_id


def test_comments_use_real_postgres_constraints_and_soft_delete(repo: PostgresRepository) -> None:
    service, _contact, claim_id = _sent_claim_with_contact(repo)
    invitation = service.create_invitation(USER_ID, ReimbursementInvitationCreate(contact_id=_contact["id"], claim_id=claim_id))
    service.accept_invitation(_guest(), ReimbursementInvitationAccept(token=invitation.accept_token))

    owner_comment = service.create_comment(_guest(USER_ID, "owner@example.com"), claim_id, ReimbursementCommentCreate(body=" Primeiro "))
    guest_comment = service.create_comment(_guest(GUEST_ID, "mae@example.com"), claim_id, ReimbursementCommentCreate(body="Segundo"))
    comments = service.list_comments(USER_ID, claim_id)
    assert [item.body for item in comments] == ["Primeiro", "Segundo"]
    assert comments[0].author_role.value == "owner"
    assert comments[1].author_role.value == "guest"

    with pytest.raises(AppError) as other_guest_error:
        service.list_comments(OTHER_GUEST_ID, claim_id)
    assert other_guest_error.value.code == "reimbursement_claim_not_found"

    with pytest.raises(AppError) as forbidden_delete:
        service.delete_comment(_guest(OTHER_GUEST_ID, "other@example.com"), claim_id, guest_comment.id)
    assert forbidden_delete.value.code == "reimbursement_claim_not_found"

    service.delete_comment(_guest(USER_ID, "owner@example.com"), claim_id, guest_comment.id)
    assert [item.id for item in service.list_comments(USER_ID, claim_id)] == [owner_comment.id]
    stored = repo.get_reimbursement_comment(USER_ID, guest_comment.id)
    assert stored is not None
    assert stored["deleted_at"] is not None

    with repo._connect() as conn, conn.cursor() as cur:
        with pytest.raises(Exception):
            cur.execute(
                """
                insert into reimbursement_comments
                  (owner_user_id, claim_id, author_user_id, author_role, body)
                values (%s, %s, %s, 'owner', '   ')
                """,
                (USER_ID, claim_id, USER_ID),
            )


def test_comment_pagination_uses_created_at_cursor(repo: PostgresRepository) -> None:
    service, _contact, claim_id = _sent_claim_with_contact(repo)
    first = service.create_comment(_guest(USER_ID, "owner@example.com"), claim_id, ReimbursementCommentCreate(body="A"))
    second = service.create_comment(_guest(USER_ID, "owner@example.com"), claim_id, ReimbursementCommentCreate(body="B"))

    page_one = service.list_comments(USER_ID, claim_id, limit=1)
    assert [item.id for item in page_one] == [first.id]
    cursor = f"{first.created_at.isoformat()}|{first.id}"
    page_two = service.list_comments(USER_ID, claim_id, limit=1, cursor=cursor)
    assert [item.id for item in page_two] == [second.id]


def test_invitation_accept_rate_limit_uses_real_postgres_lock(database_url: str, repo: PostgresRepository, monkeypatch) -> None:
    monkeypatch.setattr("app.services.reimbursement_service.settings.invitation_accept_rate_limit_enabled", True)
    monkeypatch.setattr("app.services.reimbursement_service.settings.invitation_accept_rate_limit_max_attempts", 1)
    monkeypatch.setattr("app.services.reimbursement_service.settings.invitation_accept_rate_limit_window_seconds", 60)

    def accept_invalid():
        isolated_repo = PostgresRepository(database_url, dev_user_id=USER_ID)
        try:
            return _service(isolated_repo).accept_invitation(_guest(), ReimbursementInvitationAccept(token="invalid-token-postgres-123"), client_ip="10.0.0.1")
        finally:
            isolated_repo.pool.close()

    results = _run_concurrently([accept_invalid, accept_invalid])
    assert sorted(result[1] for result in results if result[0] == "error") == [
        "reimbursement_invitation_invalid",
        "reimbursement_invitation_rate_limited",
    ]
    with repo._connect() as conn, conn.cursor() as cur:
        cur.execute("select count(*) as attempt_count from reimbursement_invitation_accept_attempts")
        assert cur.fetchone()["attempt_count"] == 2
        cur.execute("select token_hash, ip_hash from reimbursement_invitation_accept_attempts limit 1")
        attempt = cur.fetchone()
        assert len(attempt["token_hash"]) == 64
        assert len(attempt["ip_hash"]) == 64
        assert "invalid-token-postgres-123" not in str(attempt)


def test_rate_limit_window_and_distinct_tokens_in_postgres(repo: PostgresRepository, monkeypatch) -> None:
    monkeypatch.setattr("app.services.reimbursement_service.settings.invitation_accept_rate_limit_enabled", True)
    monkeypatch.setattr("app.services.reimbursement_service.settings.invitation_accept_rate_limit_max_attempts", 1)
    monkeypatch.setattr("app.services.reimbursement_service.settings.invitation_accept_rate_limit_window_seconds", 60)
    service = _service(repo)

    with pytest.raises(AppError) as first:
        service.accept_invitation(_guest(), ReimbursementInvitationAccept(token="invalid-token-window-a"), client_ip="10.0.0.2")
    assert first.value.code == "reimbursement_invitation_invalid"
    with pytest.raises(AppError) as blocked:
        service.accept_invitation(_guest(), ReimbursementInvitationAccept(token="invalid-token-window-a"), client_ip="10.0.0.2")
    assert blocked.value.code == "reimbursement_invitation_rate_limited"

    with repo._connect() as conn, conn.cursor() as cur:
        cur.execute("update reimbursement_invitation_accept_attempts set attempted_at = now() - interval '2 minutes'")

    with pytest.raises(AppError) as after_window:
        service.accept_invitation(_guest(), ReimbursementInvitationAccept(token="invalid-token-window-a"), client_ip="10.0.0.2")
    assert after_window.value.code == "reimbursement_invitation_invalid"

    with pytest.raises(AppError) as distinct_token:
        service.accept_invitation(_guest(), ReimbursementInvitationAccept(token="invalid-token-window-b"), client_ip="10.0.0.2")
    assert distinct_token.value.code == "reimbursement_invitation_invalid"


def test_migrations_apply_009_010_011_and_are_skipped_on_second_run(database_url: str) -> None:
    applied_again = apply_migrations(database_url, reset=False)
    assert applied_again == []
    repository = PostgresRepository(database_url, dev_user_id=USER_ID)
    try:
        with repository._connect() as conn, conn.cursor() as cur:
            cur.execute("select version from schema_migrations order by version")
            versions = [row["version"] for row in cur.fetchall()]
            assert "009_reimbursement_comments.sql" in versions
            assert "010_invitation_accept_rate_limits.sql" in versions
            assert "011_reimbursements_security_hardening.sql" in versions
            cur.execute(
                """
                select table_name
                from information_schema.tables
                where table_schema = 'public'
                  and table_name in ('reimbursement_comments', 'reimbursement_invitation_accept_attempts')
                order by table_name
                """
            )
            assert [row["table_name"] for row in cur.fetchall()] == [
                "reimbursement_comments",
                "reimbursement_invitation_accept_attempts",
            ]
            cur.execute(
                """
                select indexname
                from pg_indexes
                where schemaname = 'public'
                  and indexname in (
                    'reimbursement_comments_claim_active_idx',
                    'reimbursement_invitation_attempts_window_idx'
                  )
                order by indexname
                """
            )
            assert [row["indexname"] for row in cur.fetchall()] == [
                "reimbursement_comments_claim_active_idx",
                "reimbursement_invitation_attempts_window_idx",
            ]
            cur.execute(
                """
                select relname, relrowsecurity
                from pg_class
                where relnamespace = 'public'::regnamespace
                  and relname in (
                    'transactions',
                    'stored_files',
                    'transaction_attachments',
                    'reimbursement_claims',
                    'reimbursement_items',
                    'reimbursement_invitations',
                    'reimbursement_memberships',
                    'reimbursement_claim_attachments',
                    'reimbursement_comments',
                    'reimbursement_invitation_accept_attempts'
                  )
                order by relname
                """
            )
            rls = {row["relname"]: row["relrowsecurity"] for row in cur.fetchall()}
            assert all(rls.values())
            cur.execute(
                """
                select grantee, table_name, privilege_type
                from information_schema.role_table_grants
                where table_schema = 'public'
                  and grantee in ('PUBLIC', 'anon', 'authenticated')
                  and table_name in (
                    'transactions',
                    'stored_files',
                    'transaction_attachments',
                    'reimbursement_claims',
                    'reimbursement_items',
                    'reimbursement_invitations',
                    'reimbursement_memberships',
                    'reimbursement_claim_attachments',
                    'reimbursement_comments',
                    'reimbursement_invitation_accept_attempts'
                  )
                """
            )
            assert cur.fetchall() == []
    finally:
        repository.pool.close()

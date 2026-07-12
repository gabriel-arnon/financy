from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi.testclient import TestClient
from app.api import files as files_api
from app.api import deps
from app.core.config import settings
from app.main import app
from app.repositories.local_json import LocalJsonRepository
from app.services.file_storage_service import FileService, PrivateFileStorage


USER_ID = settings.dev_user_id
OTHER_USER_ID = "00000000-0000-4000-8000-000000000222"
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
WEBP_BYTES = b"RIFF" + b"\x24\x00\x00\x00" + b"WEBP" + b"\x00" * 32
PDF_BYTES = b"%PDF-1.4\n%fake\n"


def _client_with_repo(tmp_path: Path, monkeypatch) -> tuple[TestClient, LocalJsonRepository]:
    repo = LocalJsonRepository(tmp_path)
    monkeypatch.setattr(deps, "repository", repo)
    monkeypatch.setattr(settings, "upload_dir", tmp_path)
    monkeypatch.setattr(settings, "environment", "local")
    monkeypatch.setattr(settings, "private_files_enabled", True)
    monkeypatch.setattr(settings, "private_files_backend", "local")
    monkeypatch.setattr(settings, "private_files_max_size_bytes", 10 * 1024 * 1024)
    monkeypatch.setattr(settings, "private_files_allowed_mime_types", "image/jpeg,image/png,image/webp,application/pdf")
    monkeypatch.setattr(settings, "private_files_scan_provider", "mock")
    monkeypatch.setattr(settings, "private_files_orphan_retention_hours", 24)
    app.dependency_overrides.clear()
    return TestClient(app, raise_server_exceptions=False), repo


def _seed_transaction(repo: LocalJsonRepository) -> dict:
    account = repo.create_account(
        USER_ID,
        {
            "name": f"Conta Arquivo {str(uuid4())[:8]}",
            "institution": "Banco Teste",
            "type": "checking",
            "balance": "0",
            "status": "active",
        },
    )
    transaction = repo.create_transaction(
        USER_ID,
        {
            "account_id": account["id"],
            "transaction_date": "2026-07-10",
            "description": "COMPRA COM COMPROVANTE",
            "original_description": "COMPRA COM COMPROVANTE",
            "amount": "99.90",
            "type": "expense",
            "status": "confirmed",
        },
    )
    return transaction


def _override_user(user_id: str) -> None:
    app.dependency_overrides[files_api.get_request_user_id] = lambda: user_id


def _upload_file(client: TestClient, name: str, content: bytes, mime_type: str):
    return client.post("/files/upload", files={"file": (name, content, mime_type)})


def test_upload_attach_signed_download_and_remove_transaction_attachment(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    transaction = _seed_transaction(repo)

    uploaded = client.post(
        "/files/upload",
        files={"file": ("comprovante.png", PNG_BYTES, "image/png")},
    )
    assert uploaded.status_code == 200
    file_body = uploaded.json()
    assert file_body["original_filename"] == "comprovante.png"
    assert file_body["detected_mime_type"] == "image/png"
    assert file_body["status"] == "available"
    assert "storage_path" not in file_body
    assert "storage_bucket" not in file_body

    attached = client.post(
        f"/transactions/{transaction['id']}/attachments",
        json={"file_id": file_body["id"]},
    )
    assert attached.status_code == 200
    attachment = attached.json()
    assert attachment["transaction_id"] == transaction["id"]
    assert attachment["file"]["id"] == file_body["id"]

    listed = client.get(f"/transactions/{transaction['id']}/attachments")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [attachment["id"]]

    signed = client.get(f"/files/{file_body['id']}/signed-url")
    assert signed.status_code == 200
    signed_path = urlparse(signed.json()["url"]).path + "?" + urlparse(signed.json()["url"]).query
    downloaded = client.get(signed_path)
    assert downloaded.status_code == 200
    assert downloaded.content == PNG_BYTES

    removed = client.delete(f"/transactions/{transaction['id']}/attachments/{attachment['id']}")
    assert removed.status_code == 200
    assert removed.json()["status"] == "deleted"
    assert client.get(f"/transactions/{transaction['id']}/attachments").json() == []


def test_upload_rejects_mime_mismatch(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client_with_repo(tmp_path, monkeypatch)

    response = client.post(
        "/files/upload",
        files={"file": ("comprovante.jpg", b"%PDF-1.4 fake", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_file_extension"


def test_upload_rejects_file_above_limit(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client_with_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "private_files_max_size_bytes", 8)

    response = client.post(
        "/files/upload",
        files={"file": ("comprovante.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_upload_accepts_allowed_file_types_and_calculates_hash(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client_with_repo(tmp_path, monkeypatch)

    cases = [
        ("foto.jpg", JPEG_BYTES, "image/jpeg"),
        ("foto.png", PNG_BYTES, "image/png"),
        ("foto.webp", WEBP_BYTES, "image/webp"),
        ("documento.pdf", PDF_BYTES, "application/pdf"),
    ]

    for filename, content, mime_type in cases:
        response = _upload_file(client, filename, content, mime_type)
        assert response.status_code == 200
        body = response.json()
        assert body["detected_mime_type"] == mime_type
        assert len(body["sha256_hash"]) == 64


def test_upload_rejects_empty_and_unknown_magic_bytes(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client_with_repo(tmp_path, monkeypatch)

    empty = _upload_file(client, "vazio.png", b"", "image/png")
    assert empty.status_code == 400
    assert empty.json()["error"]["code"] == "empty_file"

    unknown = _upload_file(client, "texto.png", b"not an image", "image/png")
    assert unknown.status_code == 400
    assert unknown.json()["error"]["code"] == "invalid_file_type"


def test_same_hash_for_different_owners_stays_isolated(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)

    _override_user(USER_ID)
    first = _upload_file(client, "a.png", PNG_BYTES, "image/png").json()
    _override_user(OTHER_USER_ID)
    second = _upload_file(client, "b.png", PNG_BYTES, "image/png").json()

    assert first["sha256_hash"] == second["sha256_hash"]
    assert first["owner_user_id"] == USER_ID
    assert second["owner_user_id"] == OTHER_USER_ID
    assert repo.get_stored_file(USER_ID, second["id"]) is None
    assert repo.get_stored_file(OTHER_USER_ID, first["id"]) is None
    app.dependency_overrides.clear()


def test_owner_cannot_access_or_attach_other_owner_file_or_transaction(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    own_transaction = _seed_transaction(repo)
    other_account = repo.create_account(
        OTHER_USER_ID,
        {
            "name": "Conta Outro",
            "institution": "Banco Teste",
            "type": "checking",
            "balance": "0",
            "status": "active",
        },
    )
    other_transaction = repo.create_transaction(
        OTHER_USER_ID,
        {
            "account_id": other_account["id"],
            "transaction_date": "2026-07-10",
            "description": "COMPRA OUTRO OWNER",
            "original_description": "COMPRA OUTRO OWNER",
            "amount": "40.00",
            "type": "expense",
            "status": "confirmed",
        },
    )

    _override_user(OTHER_USER_ID)
    other_file = _upload_file(client, "outro.png", PNG_BYTES, "image/png").json()

    _override_user(USER_ID)
    assert client.get(f"/files/{other_file['id']}/signed-url").status_code == 404
    attach_other_file = client.post(f"/transactions/{own_transaction['id']}/attachments", json={"file_id": other_file["id"]})
    assert attach_other_file.status_code == 404

    own_file = _upload_file(client, "meu.png", PNG_BYTES, "image/png").json()
    attach_other_transaction = client.post(f"/transactions/{other_transaction['id']}/attachments", json={"file_id": own_file["id"]})
    assert attach_other_transaction.status_code == 404
    app.dependency_overrides.clear()


def test_deleted_quarantined_and_suspicious_files_do_not_generate_signed_url(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    uploaded = _upload_file(client, "comprovante.png", PNG_BYTES, "image/png").json()

    deleted = client.delete(f"/files/{uploaded['id']}")
    assert deleted.status_code == 200
    assert client.get(f"/files/{uploaded['id']}/signed-url").status_code == 404

    quarantined = _upload_file(client, "quarentena.png", PNG_BYTES, "image/png").json()
    repo.update_stored_file(USER_ID, quarantined["id"], {"status": "quarantined", "scan_status": "pending"})
    denied_quarantine = client.get(f"/files/{quarantined['id']}/signed-url")
    assert denied_quarantine.status_code == 403
    assert denied_quarantine.json()["error"]["code"] == "file_not_available"

    suspicious = _upload_file(client, "suspeito.png", PNG_BYTES, "image/png").json()
    repo.update_stored_file(USER_ID, suspicious["id"], {"status": "available", "scan_status": "suspicious"})
    denied_suspicious = client.get(f"/files/{suspicious['id']}/signed-url")
    assert denied_suspicious.status_code == 403
    assert denied_suspicious.json()["error"]["code"] == "file_not_scanned"


def test_production_without_real_scan_keeps_file_quarantined(tmp_path: Path, monkeypatch) -> None:
    client, _ = _client_with_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "private_files_scan_provider", "mock")
    _override_user(USER_ID)

    uploaded = _upload_file(client, "comprovante.png", PNG_BYTES, "image/png")

    assert uploaded.status_code == 200
    body = uploaded.json()
    assert body["status"] == "quarantined"
    assert body["scan_status"] == "pending"
    assert client.get(f"/files/{body['id']}/signed-url").status_code == 403
    app.dependency_overrides.clear()


def test_orphan_files_are_identified_after_retention_window(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "private_files_orphan_retention_hours", 0)
    service = FileService(repository=repo, settings=settings)
    transaction = _seed_transaction(repo)
    orphan = _upload_file(client, "orphan.png", PNG_BYTES, "image/png").json()
    linked = _upload_file(client, "linked.png", PNG_BYTES, "image/png").json()
    client.post(f"/transactions/{transaction['id']}/attachments", json={"file_id": linked["id"]})

    orphan_ids = {item.id for item in service.list_orphan_files(user_id=USER_ID)}

    assert orphan["id"] in orphan_ids
    assert linked["id"] not in orphan_ids


def test_storage_upload_failure_does_not_create_metadata(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)

    def fail_save(self, *, path: str, content: bytes, mime_type: str) -> None:
        raise RuntimeError("storage down")

    monkeypatch.setattr(PrivateFileStorage, "save", fail_save)
    response = _upload_file(client, "falha.png", PNG_BYTES, "image/png")

    assert response.status_code == 500
    assert repo._read().get("stored_files", []) == []


def test_database_failure_after_upload_removes_local_object(tmp_path: Path, monkeypatch) -> None:
    client, repo = _client_with_repo(tmp_path, monkeypatch)

    def fail_create(user_id: str, payload: dict):
        raise RuntimeError("db down")

    repo.create_stored_file = fail_create  # type: ignore[method-assign]
    response = _upload_file(client, "compensar.png", PNG_BYTES, "image/png")

    assert response.status_code == 500
    private_root = tmp_path / "private_files"
    assert not list(private_root.rglob("*.png"))

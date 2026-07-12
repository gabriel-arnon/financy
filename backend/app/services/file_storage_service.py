from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import Settings
from app.core.errors import AppError
from app.models.enums import StoredFileScanStatus, StoredFileStatus
from app.schemas.files import FileSignedUrlRead, StoredFileRead, TransactionAttachmentRead


ALLOWED_EXTENSIONS_BY_MIME = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
    "application/pdf": {".pdf"},
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _detect_mime(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    return None


class PrivateFileStorage:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.backend = settings.private_files_backend.strip().lower()
        self.bucket = settings.private_files_bucket
        self.local_root = settings.upload_dir / "private_files"

    def save(self, *, path: str, content: bytes, mime_type: str) -> None:
        if self.backend == "supabase":
            self._save_supabase(path=path, content=content, mime_type=mime_type)
            return
        target = self.local_root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def delete(self, *, path: str) -> None:
        if self.backend == "supabase":
            self._delete_supabase(path=path)
            return
        target = self.open_local(path)
        target.unlink(missing_ok=True)

    def open_local(self, path: str) -> Path:
        if self.backend != "local":
            raise AppError("Download local indisponivel para o storage configurado.", status_code=400, code="file_download_unavailable")
        target = (self.local_root / path).resolve()
        root = self.local_root.resolve()
        if not str(target).startswith(str(root)) or not target.exists():
            raise AppError("Arquivo nao encontrado.", status_code=404, code="file_object_not_found")
        return target

    def signed_url(self, *, path: str, expires_in: int) -> str | None:
        if self.backend != "supabase":
            return None
        if not self.settings.supabase_url or not self.settings.supabase_service_role_key:
            raise AppError("Supabase Storage nao esta configurado.", status_code=500, code="storage_not_configured")
        endpoint = f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/sign/{self.bucket}/{urllib.parse.quote(path)}"
        body = json.dumps({"expiresIn": expires_in}).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
                "apikey": self.settings.supabase_service_role_key,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise AppError("Falha ao gerar URL assinada.", status_code=502, code="storage_signed_url_failed") from exc
        signed_url = payload.get("signedURL") or payload.get("signedUrl")
        if not signed_url:
            raise AppError("Storage nao retornou URL assinada.", status_code=502, code="storage_signed_url_failed")
        if signed_url.startswith("http"):
            return signed_url
        return f"{self.settings.supabase_url.rstrip('/')}"+signed_url

    def _save_supabase(self, *, path: str, content: bytes, mime_type: str) -> None:
        if not self.settings.supabase_url or not self.settings.supabase_service_role_key:
            raise AppError("Supabase Storage nao esta configurado.", status_code=500, code="storage_not_configured")
        endpoint = f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/{self.bucket}/{urllib.parse.quote(path)}"
        request = urllib.request.Request(
            endpoint,
            data=content,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
                "apikey": self.settings.supabase_service_role_key,
                "Content-Type": mime_type,
                "x-upsert": "false",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20):
                return
        except urllib.error.HTTPError as exc:
            raise AppError("Falha ao salvar arquivo no storage.", status_code=502, code="storage_upload_failed") from exc

    def _delete_supabase(self, *, path: str) -> None:
        if not self.settings.supabase_url or not self.settings.supabase_service_role_key:
            raise AppError("Supabase Storage nao esta configurado.", status_code=500, code="storage_not_configured")
        endpoint = f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/{self.bucket}/{urllib.parse.quote(path)}"
        request = urllib.request.Request(
            endpoint,
            method="DELETE",
            headers={
                "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
                "apikey": self.settings.supabase_service_role_key,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=10):
                return
        except urllib.error.HTTPError as exc:
            raise AppError("Falha ao remover arquivo do storage.", status_code=502, code="storage_delete_failed") from exc


class FileService:
    def __init__(self, repository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings
        self._validate_config()
        self.storage = PrivateFileStorage(settings)

    def _validate_config(self) -> None:
        if not self.settings.private_files_enabled:
            raise AppError("Arquivos privados estao desabilitados.", status_code=503, code="private_files_disabled")
        backend = self.settings.private_files_backend.strip().lower()
        if backend not in {"local", "supabase"}:
            raise AppError("Provider de arquivos privados invalido.", status_code=500, code="private_files_provider_invalid")
        if backend == "supabase" and (not self.settings.supabase_url or not self.settings.supabase_service_role_key):
            raise AppError("Supabase Storage nao esta configurado.", status_code=500, code="storage_not_configured")
        if self.settings.private_files_max_size_bytes <= 0:
            raise AppError("Limite de arquivo privado invalido.", status_code=500, code="private_files_limit_invalid")

    async def upload(self, *, user_id: str, file: UploadFile, source: str = "manual") -> StoredFileRead:
        if not file.filename:
            raise AppError("Arquivo sem nome.", code="invalid_file")
        content = await file.read()
        if not content:
            raise AppError("Arquivo vazio.", code="empty_file")
        if len(content) > self.settings.private_files_max_size_bytes:
            raise AppError("Arquivo acima do limite permitido.", status_code=413, code="file_too_large")

        original_filename = Path(file.filename).name
        extension = Path(original_filename).suffix.lower()
        detected_mime = _detect_mime(content)
        declared_mime = file.content_type
        allowed_mime_types = set(self.settings.private_files_allowed_mime_type_list)
        if not detected_mime or detected_mime not in ALLOWED_EXTENSIONS_BY_MIME or detected_mime not in allowed_mime_types:
            raise AppError("Tipo de arquivo nao permitido.", code="invalid_file_type")
        if extension not in ALLOWED_EXTENSIONS_BY_MIME[detected_mime]:
            raise AppError("Extensao do arquivo nao confere com o conteudo.", code="invalid_file_extension")
        if declared_mime and declared_mime not in ALLOWED_EXTENSIONS_BY_MIME:
            raise AppError("MIME type declarado nao permitido.", code="invalid_mime_type")
        if declared_mime and declared_mime != detected_mime:
            raise AppError("MIME type declarado nao confere com o conteudo.", code="mime_type_mismatch")

        file_id = str(uuid4())
        sha256_hash = hashlib.sha256(content).hexdigest()
        storage_path = f"user/{user_id}/files/{file_id}{extension}"
        status, scan_status = self._initial_security_state()
        self.storage.save(path=storage_path, content=content, mime_type=detected_mime)
        try:
            record = self.repository.create_stored_file(
                user_id,
                {
                    "id": file_id,
                    "storage_bucket": self.storage.bucket,
                    "storage_path": storage_path,
                    "original_filename": original_filename,
                    "declared_mime_type": declared_mime,
                    "detected_mime_type": detected_mime,
                    "size_bytes": len(content),
                    "sha256_hash": sha256_hash,
                    "source": source,
                    "status": status,
                    "scan_status": scan_status,
                    "metadata": {},
                },
            )
        except Exception:
            try:
                self.storage.delete(path=storage_path)
            except Exception:
                pass
            raise
        self._event(user_id, file_id, "file_uploaded", {"source": source, "size_bytes": len(content)})
        return StoredFileRead(**record)

    def _initial_security_state(self) -> tuple[str, str]:
        provider = self.settings.private_files_scan_provider.strip().lower()
        environment = self.settings.environment.lower()
        if provider == "mock" and environment in {"local", "development", "test"}:
            return StoredFileStatus.available.value, StoredFileScanStatus.skipped.value
        return StoredFileStatus.quarantined.value, StoredFileScanStatus.pending.value

    def get(self, *, user_id: str, file_id: str) -> StoredFileRead:
        record = self._get_record(user_id=user_id, file_id=file_id)
        return StoredFileRead(**record)

    def _get_record(self, *, user_id: str, file_id: str) -> dict[str, Any]:
        record = self.repository.get_stored_file(user_id, file_id)
        if not record or record.get("status") == StoredFileStatus.deleted.value:
            raise AppError("Arquivo nao encontrado.", status_code=404, code="file_not_found")
        return record

    def delete(self, *, user_id: str, file_id: str) -> StoredFileRead:
        current = self._get_record(user_id=user_id, file_id=file_id)
        record = self.repository.update_stored_file(
            user_id,
            file_id,
            {"status": StoredFileStatus.deleted.value, "deleted_at": _utcnow()},
        )
        self._event(user_id, file_id, "file_deleted", {})
        return StoredFileRead(**(record or current))

    def signed_url(self, *, user_id: str, file_id: str, base_url: str = "") -> FileSignedUrlRead:
        stored_file = self._get_record(user_id=user_id, file_id=file_id)
        if stored_file.get("status") != StoredFileStatus.available.value:
            raise AppError("Arquivo indisponivel para download.", status_code=403, code="file_not_available")
        if stored_file.get("scan_status") not in {StoredFileScanStatus.clean.value, StoredFileScanStatus.skipped.value}:
            raise AppError("Arquivo ainda nao foi liberado para download.", status_code=403, code="file_not_scanned")
        expires_at = _utcnow() + timedelta(seconds=self.settings.private_files_signed_url_ttl_seconds)
        storage_url = self.storage.signed_url(path=stored_file["storage_path"], expires_in=self.settings.private_files_signed_url_ttl_seconds)
        url = storage_url or self._local_signed_url(file_id=file_id, expires_at=expires_at, base_url=base_url)
        self._event(user_id, file_id, "attachment_url_generated", {"expires_at": expires_at.isoformat()})
        return FileSignedUrlRead(file_id=file_id, url=url, expires_at=expires_at)

    def local_download_path(self, *, file_id: str, expires: int, token: str) -> Path:
        if expires < int(time.time()):
            raise AppError("URL expirada.", status_code=403, code="signed_url_expired")
        expected = self._download_signature(file_id=file_id, expires=expires)
        if not hmac.compare_digest(expected, token):
            raise AppError("URL invalida.", status_code=403, code="invalid_signed_url")
        record = self.repository._fetch_one("select * from stored_files where id = %s", (file_id,)) if hasattr(self.repository, "_fetch_one") else None
        if record is None:
            record = self._find_local_file_without_user(file_id)
        if not record or record.get("status") != StoredFileStatus.available.value:
            raise AppError("Arquivo nao encontrado.", status_code=404, code="file_not_found")
        if record.get("scan_status") not in {StoredFileScanStatus.clean.value, StoredFileScanStatus.skipped.value}:
            raise AppError("Arquivo nao encontrado.", status_code=404, code="file_not_found")
        return self.storage.open_local(record["storage_path"])

    def attach_to_transaction(self, *, user_id: str, transaction_id: str, file_id: str) -> TransactionAttachmentRead:
        transaction = self.repository.get_transaction(user_id, transaction_id)
        if not transaction:
            raise AppError("Transacao nao encontrada.", status_code=404, code="transaction_not_found")
        stored_file = self.get(user_id=user_id, file_id=file_id)
        attachment = self.repository.create_transaction_attachment(
            user_id,
            {"transaction_id": transaction_id, "file_id": file_id},
        )
        self._event(user_id, file_id, "transaction_attachment_created", {"transaction_id": transaction_id})
        return self._attachment_read(attachment, stored_file.model_dump(mode="json"))

    def list_transaction_attachments(self, *, user_id: str, transaction_id: str) -> list[TransactionAttachmentRead]:
        if not self.repository.get_transaction(user_id, transaction_id):
            raise AppError("Transacao nao encontrada.", status_code=404, code="transaction_not_found")
        return [self._attachment_from_joined(row) for row in self.repository.list_transaction_attachments(user_id, transaction_id)]

    def delete_transaction_attachment(self, *, user_id: str, transaction_id: str, attachment_id: str) -> dict[str, str]:
        attachment = self.repository.get_transaction_attachment(user_id, attachment_id)
        if not attachment or attachment.get("transaction_id") != transaction_id:
            raise AppError("Anexo nao encontrado.", status_code=404, code="attachment_not_found")
        deleted = self.repository.delete_transaction_attachment(user_id, attachment_id)
        self._event(user_id, attachment["file_id"], "transaction_attachment_deleted", {"transaction_id": transaction_id})
        if not deleted:
            raise AppError("Anexo nao encontrado.", status_code=404, code="attachment_not_found")
        return {"status": "deleted"}

    def list_orphan_files(self, *, user_id: str) -> list[StoredFileRead]:
        list_orphans = getattr(self.repository, "list_orphan_stored_files", None)
        if not list_orphans:
            return []
        cutoff = _utcnow() - timedelta(hours=self.settings.private_files_orphan_retention_hours)
        return [StoredFileRead(**item) for item in list_orphans(user_id, cutoff)]

    def _attachment_from_joined(self, row: dict[str, Any]) -> TransactionAttachmentRead:
        file_data = {
            "id": row["file_id"],
            "owner_user_id": row["owner_user_id"],
            "storage_bucket": row["storage_bucket"],
            "storage_path": row["storage_path"],
            "original_filename": row["original_filename"],
            "declared_mime_type": row.get("declared_mime_type"),
            "detected_mime_type": row["detected_mime_type"],
            "size_bytes": row["size_bytes"],
            "sha256_hash": row["sha256_hash"],
            "source": row["source"],
            "status": row["file_status"],
            "scan_status": row["scan_status"],
            "metadata": row.get("metadata") or {},
            "created_at": row["file_created_at"],
            "deleted_at": row.get("file_deleted_at"),
        }
        return self._attachment_read(row, file_data)

    def _attachment_read(self, attachment: dict[str, Any], file_data: dict[str, Any]) -> TransactionAttachmentRead:
        return TransactionAttachmentRead(
            id=attachment["id"],
            owner_user_id=attachment["owner_user_id"],
            transaction_id=attachment["transaction_id"],
            file_id=attachment["file_id"],
            status=attachment.get("status", "active"),
            created_at=attachment["created_at"],
            deleted_at=attachment.get("deleted_at"),
            file=StoredFileRead(**file_data),
        )

    def _local_signed_url(self, *, file_id: str, expires_at: datetime, base_url: str) -> str:
        expires = int(expires_at.timestamp())
        token = self._download_signature(file_id=file_id, expires=expires)
        path = f"/files/{file_id}/download?expires={expires}&token={urllib.parse.quote(token)}"
        return f"{base_url.rstrip('/')}{path}" if base_url else path

    def _download_signature(self, *, file_id: str, expires: int) -> str:
        message = f"{file_id}:{expires}".encode("utf-8")
        return hmac.new(self.settings.jwt_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    def _find_local_file_without_user(self, file_id: str) -> dict[str, Any] | None:
        data = self.repository._read() if hasattr(self.repository, "_read") else {}
        for item in data.get("stored_files", []):
            if item.get("id") == file_id:
                return item
        return None

    def _event(self, user_id: str, file_id: str, event_type: str, metadata: dict[str, Any]) -> None:
        create_event = getattr(self.repository, "create_stored_file_event", None)
        if not create_event:
            return
        create_event(
            user_id,
            {
                "file_id": file_id,
                "actor_type": "owner",
                "actor_user_id": user_id,
                "event_type": event_type,
                "metadata": metadata,
            },
        )

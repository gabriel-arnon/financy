from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import EntityStatus, StoredFileScanStatus, StoredFileStatus


class StoredFileRead(BaseModel):
    id: str
    owner_user_id: str
    original_filename: str
    declared_mime_type: str | None = None
    detected_mime_type: str
    size_bytes: int
    sha256_hash: str
    source: str
    status: StoredFileStatus
    scan_status: StoredFileScanStatus
    metadata: dict[str, Any] = {}
    created_at: datetime
    deleted_at: datetime | None = None


class FileSignedUrlRead(BaseModel):
    file_id: str
    url: str
    expires_at: datetime


class TransactionAttachmentCreate(BaseModel):
    file_id: str


class TransactionAttachmentRead(BaseModel):
    id: str
    owner_user_id: str
    transaction_id: str
    file_id: str
    status: EntityStatus
    created_at: datetime
    deleted_at: datetime | None = None
    file: StoredFileRead

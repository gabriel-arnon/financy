from __future__ import annotations

from app.core.config import Settings
from app.repositories.local_json import LocalJsonRepository
from app.repositories.postgres import PostgresRepository


def create_repository(settings: Settings):
    backend = settings.storage_backend.strip().lower()
    if backend in ("json", "local_json", "local-json"):
        return LocalJsonRepository(settings.upload_dir)
    if backend in ("postgres", "postgresql"):
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is required when STORAGE_BACKEND=postgres.")
        return PostgresRepository(settings.database_url, dev_user_id=settings.dev_user_id)
    raise RuntimeError(f"Unsupported STORAGE_BACKEND: {settings.storage_backend}")

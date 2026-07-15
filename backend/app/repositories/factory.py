from __future__ import annotations

import os

from app.core.config import Settings
from app.repositories.local_json import LocalJsonRepository
from app.repositories.postgres import PostgresRepository


REMOTE_RUNTIME_ENV_KEYS = ("RENDER", "RENDER_SERVICE_ID", "RENDER_EXTERNAL_URL", "RAILWAY_ENVIRONMENT", "FLY_APP_NAME")
LOCAL_ENVIRONMENTS = {"local", "development", "test"}


def _is_remote_runtime(settings: Settings) -> bool:
    environment = settings.environment.strip().lower()
    return environment not in LOCAL_ENVIRONMENTS or any(os.getenv(key) for key in REMOTE_RUNTIME_ENV_KEYS)


def create_repository(settings: Settings):
    backend = settings.storage_backend.strip().lower()
    if backend in ("json", "local_json", "local-json"):
        if _is_remote_runtime(settings):
            raise RuntimeError(
                "STORAGE_BACKEND=json is only allowed in local/development/test. "
                "Configure STORAGE_BACKEND=postgres and DATABASE_URL for deployed environments."
            )
        return LocalJsonRepository(settings.upload_dir)
    if backend in ("postgres", "postgresql"):
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is required when STORAGE_BACKEND=postgres.")
        return PostgresRepository(settings.database_url, dev_user_id=settings.dev_user_id)
    raise RuntimeError(f"Unsupported STORAGE_BACKEND: {settings.storage_backend}")

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.repositories.factory import create_repository
from app.repositories.local_json import LocalJsonRepository


def test_json_repository_is_allowed_locally(tmp_path, monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    settings = Settings(APP_ENV="local", STORAGE_BACKEND="json", UPLOAD_STORAGE_PATH=tmp_path)

    repository = create_repository(settings)

    assert isinstance(repository, LocalJsonRepository)


def test_json_repository_is_rejected_in_production(tmp_path):
    settings = Settings(APP_ENV="production", STORAGE_BACKEND="json", UPLOAD_STORAGE_PATH=tmp_path)

    with pytest.raises(RuntimeError, match="STORAGE_BACKEND=json"):
        create_repository(settings)


def test_json_repository_is_rejected_on_render_even_without_app_env(tmp_path, monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    settings = Settings(APP_ENV="local", STORAGE_BACKEND="json", UPLOAD_STORAGE_PATH=tmp_path)

    with pytest.raises(RuntimeError, match="STORAGE_BACKEND=json"):
        create_repository(settings)

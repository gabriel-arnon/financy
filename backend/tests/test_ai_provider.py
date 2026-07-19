from types import SimpleNamespace

import httpx
import pytest

from app.core.errors import AppError
from app.services.ai_provider import AiProviderClient


def _settings(**overrides):
    values = {
        "ai_enabled": True,
        "ai_provider": "openai-compatible",
        "ai_base_url": "https://example.test/v1",
        "ai_api_key": "secret",
        "ai_model": "test-model",
        "ai_timeout_seconds": 12,
        "ai_import_provider": "openai-compatible",
        "ai_import_base_url": "https://api.openai.com/v1",
        "ai_import_api_key": None,
        "ai_import_model": "gpt-4o-mini",
        "ai_import_timeout_seconds": 45,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self):
        return {"choices": [{"message": {"content": '{"ok": true, "count": 2}'}}]}


def test_ai_provider_posts_openai_compatible_json(monkeypatch) -> None:
    calls = []

    def fake_post(url, *, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = AiProviderClient(_settings())

    result = provider.chat_json([{"role": "user", "content": "teste"}])

    assert result == {"ok": True, "count": 2}
    assert calls[0]["url"] == "https://example.test/v1/chat/completions"
    assert calls[0]["headers"]["Authorization"] == "Bearer secret"
    assert calls[0]["json"]["response_format"] == {"type": "json_object"}
    assert calls[0]["json"]["model"] == "test-model"
    assert calls[0]["timeout"] == 12


def test_ai_provider_requires_configuration() -> None:
    provider = AiProviderClient(_settings(ai_enabled=False))

    with pytest.raises(AppError) as exc_info:
        provider.chat_json([{"role": "user", "content": "teste"}])

    assert exc_info.value.code == "ai_not_configured"

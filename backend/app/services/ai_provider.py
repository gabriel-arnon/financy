from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import AppError


def json_from_response(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise AppError("A IA nao retornou JSON valido.", status_code=502, code="ai_invalid_json")
    return json.loads(cleaned[start : end + 1])


class AiProviderClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.settings.ai_enabled)

    @property
    def provider_name(self) -> str:
        return self.settings.ai_provider or self.settings.ai_import_provider

    @property
    def base_url(self) -> str:
        return self.settings.ai_base_url or self.settings.ai_import_base_url

    @property
    def api_key(self) -> str | None:
        return self.settings.ai_api_key or self.settings.ai_import_api_key

    @property
    def model(self) -> str:
        return self.settings.ai_model or self.settings.ai_import_model

    @property
    def timeout_seconds(self) -> float:
        return self.settings.ai_timeout_seconds or self.settings.ai_import_timeout_seconds

    def chat_json(self, messages: list[dict[str, str]], *, code: str = "ai_provider_failed") -> dict[str, Any]:
        if not self.enabled:
            raise AppError("IA nao configurada.", status_code=400, code="ai_not_configured")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        try:
            response = httpx.post(
                self.base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return json_from_response(content)
        except AppError:
            raise
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as exc:
            raise AppError("Falha ao consultar a IA.", status_code=502, code=code) from exc

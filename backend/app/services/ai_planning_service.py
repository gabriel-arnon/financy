from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.core.errors import AppError
from app.services.ai_provider import AiProviderClient


class AiRecurringSuggestion(BaseModel):
    id: str
    name: str | None = Field(default=None, min_length=1, max_length=90)
    kind: Literal["installment", "fixed_bill", "subscription"] | None = None
    explanation: str | None = Field(default=None, max_length=240)
    confidence: float = Field(default=0.6, ge=0, le=1)


class AiRecurringSuggestionResponse(BaseModel):
    suggestions: list[AiRecurringSuggestion] = Field(default_factory=list)


def _prompt_for_recurring_suggestions(candidates: list[dict[str, Any]], categories: list[dict[str, Any]]) -> list[dict[str, str]]:
    schema_description = """
Retorne somente JSON valido:
{
  "suggestions": [{
    "id": "id recebido no candidato",
    "name": "nome curto para o recorrente",
    "kind": "installment|fixed_bill|subscription",
    "explanation": "motivo curto da sugestao",
    "confidence": 0.0
  }]
}
"""
    instructions = (
        "Voce ajuda a revisar recorrencias financeiras brasileiras. "
        "Use apenas os candidatos enviados. Nao crie recorrentes novos. "
        "Melhore nomes genericos, identifique se e parcela, conta fixa ou assinatura, "
        "e explique brevemente com base nas ocorrencias. "
        "Nao confirme nada automaticamente; a resposta e apenas sugestao para revisao humana. "
        "Evite expor detalhes sensiveis alem do que ja veio no candidato."
    )
    category_names = [item.get("name") for item in categories if item.get("status") == "active" and item.get("name")]
    content = {"categories": category_names[:80], "candidates": candidates[:20]}
    return [
        {"role": "system", "content": instructions},
        {"role": "user", "content": f"{schema_description}\n\nDados:\n{json.dumps(content, ensure_ascii=False)}"},
    ]


class AiPlanningAnalyzer:
    def __init__(self, provider: AiProviderClient) -> None:
        self.provider = provider

    @property
    def enabled(self) -> bool:
        return self.provider.enabled

    def enrich_recurring_suggestions(self, suggestions: list[dict[str, Any]], categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.enabled or not suggestions:
            return suggestions

        candidates = []
        for suggestion in suggestions:
            metadata = suggestion.get("metadata") or {}
            candidates.append(
                {
                    "id": suggestion["id"],
                    "detected_name": suggestion.get("name"),
                    "detected_kind": suggestion.get("kind"),
                    "amount": str(suggestion.get("amount")),
                    "occurrences": metadata.get("occurrences"),
                    "months": metadata.get("months"),
                    "sample_descriptions": metadata.get("sample_descriptions", [])[:5],
                    "source_counts": metadata.get("source_counts", {}),
                    "category_id": suggestion.get("category_id"),
                }
            )

        try:
            result = AiRecurringSuggestionResponse.model_validate(
                self.provider.chat_json(
                    _prompt_for_recurring_suggestions(candidates, categories),
                    code="ai_planning_recurring_failed",
                )
            )
        except (AppError, ValidationError):
            return suggestions

        enriched_by_id = {item.id: item for item in result.suggestions}
        enriched: list[dict[str, Any]] = []
        for suggestion in suggestions:
            data = dict(suggestion)
            ai_item = enriched_by_id.get(suggestion["id"])
            if ai_item:
                if ai_item.name:
                    data["name"] = ai_item.name.strip()
                if ai_item.kind:
                    data["kind"] = ai_item.kind
                if ai_item.explanation:
                    data["notes"] = ai_item.explanation.strip()
                metadata = dict(data.get("metadata") or {})
                metadata.update(
                    {
                        "ai_provider": self.provider.provider_name,
                        "ai_model": self.provider.model,
                        "ai_confidence": ai_item.confidence,
                    }
                )
                data["metadata"] = metadata
                data["source"] = "ai_suggestion"
            enriched.append(data)
        return enriched

import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import Settings
from app.core.errors import AppError
from app.models.enums import ExcludedReason, TransactionType
from app.parsers.pdf_parser import _extract_text
from app.parsers.utils import parse_brazilian_money
from app.schemas.common import IgnoredPdfLine, NormalizedTransactionPreview, ParserResult, StatementMetadata
from app.services.ai_provider import AiProviderClient


class AiCard(BaseModel):
    last_digits: str | None = None
    name: str | None = None
    brand: str | None = None
    institution: str | None = None
    limit_amount: str | None = None

    @field_validator("last_digits")
    @classmethod
    def normalize_digits(cls, value: str | None) -> str | None:
        if not value:
            return None
        digits = re.sub(r"\D", "", value)
        return digits[-4:] if len(digits) >= 4 else None


class AiTransaction(BaseModel):
    date: str
    description: str = Field(min_length=1)
    amount: str
    type: Literal["expense", "income", "transfer", "payment", "refund"] = "expense"
    card_last_digits: str | None = None
    installment_current: int | None = None
    installment_total: int | None = None
    confidence: float = Field(default=0.6, ge=0, le=1)
    selected: bool = True
    raw_text: str | None = None

    @field_validator("card_last_digits")
    @classmethod
    def normalize_card_digits(cls, value: str | None) -> str | None:
        if not value:
            return None
        digits = re.sub(r"\D", "", value)
        return digits[-4:] if len(digits) >= 4 else None


class AiIgnoredLine(BaseModel):
    raw_text: str
    reason: Literal["subtotal", "total", "saldo_anterior", "informativo", "duplicate", "payment", "refund", "low_confidence"] = "informativo"


class AiInvoiceExtraction(BaseModel):
    document_type: str | None = None
    institution: str | None = None
    statement_due_date: str | None = None
    statement_reference_month: str | None = None
    statement_total_amount: str | None = None
    card_limit_amount: str | None = None
    cards: list[AiCard] = Field(default_factory=list)
    transactions: list[AiTransaction] = Field(default_factory=list)
    ignored_lines: list[AiIgnoredLine] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)


class AiItemEnrichment(BaseModel):
    index: int
    suggested_category: str | None = None
    normalized_description: str | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    explanation: str | None = None
    duplicate_candidate: bool = False
    duplicate_reason: str | None = None
    installment_current: int | None = None
    installment_total: int | None = None
    needs_review: bool = False


class AiPreviewEnrichment(BaseModel):
    summary: str | None = None
    consistency_status: Literal["ok", "warning", "unknown"] = "unknown"
    consistency_message: str | None = None
    items: list[AiItemEnrichment] = Field(default_factory=list)


def _parse_ai_date(value: str | None) -> date | None:
    if not value:
        return None
    match = re.search(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})", value)
    if match:
        return date(int(match.group("year")), int(match.group("month")), int(match.group("day")))
    match = re.search(r"(?P<day>\d{2})/(?P<month>\d{2})/(?P<year>\d{4})", value)
    if match:
        return date(int(match.group("year")), int(match.group("month")), int(match.group("day")))
    return None


def _parse_ai_month(value: str | None) -> date | None:
    parsed = _parse_ai_date(value)
    if parsed:
        return date(parsed.year, parsed.month, 1)
    if not value:
        return None
    match = re.search(r"(?P<year>\d{4})-(?P<month>\d{2})", value)
    if match:
        return date(int(match.group("year")), int(match.group("month")), 1)
    return None


def _parse_ai_money(value: str | None) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return abs(parse_brazilian_money(str(value)))
    except ValueError:
        try:
            return abs(Decimal(str(value)))
        except Exception:
            return None


def _prompt_for_text(text: str) -> list[dict[str, str]]:
    schema_description = """
Retorne somente JSON valido com este formato:
{
  "document_type": "credit_card_statement|bank_statement|unknown",
  "institution": "nome do banco/cartao ou null",
  "statement_due_date": "YYYY-MM-DD ou null",
  "statement_reference_month": "YYYY-MM-01 ou null",
  "statement_total_amount": "1234.56 ou null",
  "card_limit_amount": "1234.56 ou null",
  "cards": [{"last_digits":"1234","name":"...","brand":"Visa","institution":"...","limit_amount":"1234.56"}],
  "transactions": [{
    "date":"YYYY-MM-DD",
    "description":"descricao sem valor/data/parcela",
    "amount":"123.45",
    "type":"expense|income|transfer|payment|refund",
    "card_last_digits":"1234 ou null",
    "installment_current":1,
    "installment_total":10,
    "confidence":0.0,
    "selected":true,
    "raw_text":"linha original"
  }],
  "ignored_lines": [{"raw_text":"linha","reason":"informativo|payment|refund|total|subtotal|saldo_anterior|duplicate|low_confidence"}],
  "confidence":0.0
}
"""
    instructions = (
        "Voce extrai dados financeiros de faturas/extratos brasileiros. "
        "Nao invente dados. Se nao encontrar um campo, use null. "
        "Nao transforme totais, boletos, opcoes de parcelamento, encargos ou textos informativos em transacoes. "
        "Pagamentos de fatura devem ser type payment e selected false ou ir para ignored_lines. "
        "Creditos/estornos devem ser type refund e selected false. "
        "Compras/despesas devem ser type expense. Preserve finais de cartao quando houver. "
        "Use valores positivos com ponto decimal, sem simbolo R$."
    )
    return [
        {"role": "system", "content": instructions},
        {"role": "user", "content": f"{schema_description}\n\nTexto extraido do PDF:\n{text[:55000]}"},
    ]


def _prompt_for_preview_items(items: list[dict[str, Any]], categories: list[dict[str, Any]], total_amount: Any | None) -> list[dict[str, str]]:
    compact_items = [
        {
            "index": index,
            "date": item.get("transaction_date"),
            "description": item.get("description"),
            "original_description": item.get("original_description"),
            "amount": str(item.get("amount")),
            "type": item.get("type"),
            "installment_current": item.get("installment_current"),
            "installment_total": item.get("installment_total"),
            "card_last_digits": item.get("card_last_digits"),
            "selected": item.get("default_selected", True),
            "needs_review": item.get("needs_review", False),
        }
        for index, item in enumerate(items)
    ]
    category_names = [category.get("name") for category in categories if category.get("status") == "active" and category.get("name")]
    schema_description = """
Retorne somente JSON valido:
{
  "summary": "resumo curto da importacao",
  "consistency_status": "ok|warning|unknown",
  "consistency_message": "mensagem curta sobre soma x total ou null",
  "items": [{
    "index": 0,
    "suggested_category": "nome exato de categoria existente ou null",
    "normalized_description": "descricao limpa ou null",
    "confidence": 0.0,
    "explanation": "motivo curto",
    "duplicate_candidate": false,
    "duplicate_reason": null,
    "installment_current": null,
    "installment_total": null,
    "needs_review": false
  }]
}
"""
    instructions = (
        "Voce revisa uma previa de importacao financeira. "
        "Use apenas categorias existentes. Nao invente categorias. "
        "Sugira descricao limpa sem alterar o significado. "
        "Marque baixa confianca quando houver ambiguidade. "
        "Nao classifique pagamentos/creditos como despesa. "
        "A resposta deve ajudar o usuario a revisar, nao confirmar automaticamente."
    )
    content = {
        "statement_total_amount": str(total_amount) if total_amount is not None else None,
        "categories": category_names,
        "items": compact_items[:120],
    }
    return [
        {"role": "system", "content": instructions},
        {"role": "user", "content": f"{schema_description}\n\nDados da previa:\n{json.dumps(content, ensure_ascii=False)}"},
    ]


class AiImportAnalyzer:
    def __init__(self, settings: Settings, provider: AiProviderClient | None = None) -> None:
        self.settings = settings
        self.provider = provider or AiProviderClient(settings)

    @property
    def enabled(self) -> bool:
        return self.provider.enabled

    def analyze_pdf(self, path: Path) -> ParserResult:
        if not self.enabled:
            raise AppError("Analise com IA nao esta configurada.", status_code=400, code="ai_import_not_configured")
        if path.suffix.lower() != ".pdf":
            raise AppError("Analise com IA esta disponivel apenas para PDF.", status_code=400, code="ai_import_pdf_only")

        text = _extract_text(path)
        if not text.strip():
            raise AppError("Nao foi possivel extrair texto do PDF para analise com IA.", status_code=400, code="ai_import_no_text")

        extraction = self._call_provider(text)
        return self._to_parser_result(extraction)

    def _call_provider(self, text: str) -> AiInvoiceExtraction:
        try:
            return AiInvoiceExtraction.model_validate(self.provider.chat_json(_prompt_for_text(text), code="ai_import_failed"))
        except (AppError, ValidationError) as exc:
            raise AppError("Falha na analise com IA. Tente novamente ou revise o arquivo manualmente.", status_code=502, code="ai_import_failed") from exc

    def enrich_preview_items(self, items: list[dict[str, Any]], categories: list[dict[str, Any]], total_amount: Any | None = None) -> AiPreviewEnrichment:
        if not self.enabled or not items:
            return AiPreviewEnrichment()

        try:
            return AiPreviewEnrichment.model_validate(
                self.provider.chat_json(_prompt_for_preview_items(items, categories, total_amount), code="ai_import_enrichment_failed")
            )
        except (AppError, ValidationError):
            return AiPreviewEnrichment(
                consistency_status="unknown",
                consistency_message="Nao foi possivel enriquecer a previa com IA.",
            )

    def _to_parser_result(self, extraction: AiInvoiceExtraction) -> ParserResult:
        first_card = extraction.cards[0] if extraction.cards else None
        metadata = StatementMetadata(
            statement_total_amount=_parse_ai_money(extraction.statement_total_amount),
            statement_due_date=_parse_ai_date(extraction.statement_due_date),
            statement_reference_month=_parse_ai_month(extraction.statement_reference_month),
            card_last_digits=first_card.last_digits if first_card else None,
            card_name=first_card.name if first_card else None,
            card_brand=first_card.brand if first_card else None,
            card_institution=extraction.institution or (first_card.institution if first_card else None),
            card_limit_amount=_parse_ai_money(extraction.card_limit_amount) or (_parse_ai_money(first_card.limit_amount) if first_card else None),
        )

        cards_by_digits = {card.last_digits: card for card in extraction.cards if card.last_digits}
        previews: list[NormalizedTransactionPreview] = []
        for tx in extraction.transactions:
            tx_date = _parse_ai_date(tx.date)
            amount = _parse_ai_money(tx.amount)
            if not tx_date or amount is None:
                continue
            card = cards_by_digits.get(tx.card_last_digits or "")
            tx_type = TransactionType(tx.type)
            confidence = min(tx.confidence, extraction.confidence)
            previews.append(
                NormalizedTransactionPreview(
                    transaction_date=tx_date,
                    description=tx.description.strip(),
                    original_description=tx.description.strip(),
                    amount=amount,
                    type=tx_type,
                    installment_current=tx.installment_current,
                    installment_total=tx.installment_total,
                    raw_text=tx.raw_text,
                    raw_row={
                        "parser": "ai_import_v1",
                        "provider": self.provider.provider_name,
                        "model": self.provider.model,
                        "source": "ai",
                    },
                    parser_confidence=confidence,
                    needs_review=True,
                    default_selected=bool(tx.selected and tx_type == TransactionType.expense and confidence >= 0.65),
                    excluded_reason=None if tx_type == TransactionType.expense else (ExcludedReason.payment if tx_type == TransactionType.payment else ExcludedReason.refund),
                    statement_total_amount=metadata.statement_total_amount,
                    statement_due_date=metadata.statement_due_date,
                    statement_reference_month=metadata.statement_reference_month,
                    card_last_digits=tx.card_last_digits,
                    card_name=card.name if card else metadata.card_name,
                    card_brand=card.brand if card else metadata.card_brand,
                    card_institution=card.institution if card else metadata.card_institution,
                    card_limit_amount=_parse_ai_money(card.limit_amount) if card else metadata.card_limit_amount,
                )
            )

        ignored = [
            IgnoredPdfLine(raw_text=item.raw_text, excluded_reason=ExcludedReason(item.reason))
            for item in extraction.ignored_lines
            if item.raw_text
        ]
        return ParserResult(items=previews, ignored_lines=ignored, statement_metadata=metadata)

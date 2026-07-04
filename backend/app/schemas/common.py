from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.enums import CategoryType, EntityStatus, ExcludedReason, PreviewStatus, TransactionType


class NormalizedTransactionPreview(BaseModel):
    transaction_date: date
    description: str = Field(min_length=1)
    original_description: str
    amount: Decimal
    type: TransactionType = TransactionType.expense
    account_id: str | None = None
    card_id: str | None = None
    card_statement_id: str | None = None
    category_id: str | None = None
    suggested_category: str | None = None
    merchant_country: str | None = None
    installment_current: int | None = None
    installment_total: int | None = None
    raw_text: str | None = None
    raw_row: dict[str, Any] | None = None
    parser_confidence: float = Field(default=0.75, ge=0, le=1)
    needs_review: bool = False
    duplicate_candidate: bool = False
    default_selected: bool = True
    excluded_reason: ExcludedReason | None = None
    classification_rule_id: str | None = None
    classification_label: str | None = None
    statement_total_amount: Decimal | None = None
    statement_due_date: date | None = None
    statement_reference_month: date | None = None
    card_last_digits: str | None = None
    card_name: str | None = None
    card_brand: str | None = None
    card_institution: str | None = None
    card_limit_amount: Decimal | None = None
    account_institution: str | None = None
    account_agency: str | None = None
    account_number: str | None = None
    account_balance: Decimal | None = None
    status: PreviewStatus = PreviewStatus.pending


class CategoryBase(BaseModel):
    name: str = Field(min_length=1)
    type: CategoryType = CategoryType.both
    status: EntityStatus = EntityStatus.active

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name nao pode ser vazio")
        return normalized


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    type: CategoryType | None = None
    status: EntityStatus | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("name nao pode ser vazio")
        return normalized


class CategoryRead(CategoryBase):
    id: str
    user_id: str | None = None
    is_system: bool = False
    created_at: datetime | None = None


class IgnoredPdfLine(BaseModel):
    raw_text: str
    excluded_reason: ExcludedReason
    section: str | None = None


class StatementMetadata(BaseModel):
    statement_total_amount: Decimal | None = None
    statement_due_date: date | None = None
    statement_reference_month: date | None = None
    card_last_digits: str | None = None
    card_name: str | None = None
    card_brand: str | None = None
    card_institution: str | None = None
    card_limit_amount: Decimal | None = None
    account_institution: str | None = None
    account_agency: str | None = None
    account_number: str | None = None
    account_balance: Decimal | None = None


class ParserResult(BaseModel):
    items: list[NormalizedTransactionPreview] = Field(default_factory=list)
    ignored_lines: list[IgnoredPdfLine] = Field(default_factory=list)
    statement_metadata: StatementMetadata = Field(default_factory=StatementMetadata)

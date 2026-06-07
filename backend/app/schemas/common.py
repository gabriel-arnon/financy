from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import PreviewStatus, TransactionType


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
    installment_current: int | None = None
    installment_total: int | None = None
    raw_text: str | None = None
    raw_row: dict[str, Any] | None = None
    parser_confidence: float = Field(default=0.75, ge=0, le=1)
    needs_review: bool = False
    duplicate_candidate: bool = False
    status: PreviewStatus = PreviewStatus.pending


class CategoryRead(BaseModel):
    id: str
    name: str

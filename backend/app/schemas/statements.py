from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.schemas.transactions import TransactionRead


class CardStatementBase(BaseModel):
    id: str
    user_id: str
    card_id: str
    account_id: str | None = None
    reference_month: str
    due_date: str | None = None
    closing_date: str | None = None
    reported_total: Decimal | None = None
    minimum_payment_amount: Decimal | None = None
    status: str
    paid_at: datetime | None = None
    source_file_id: str | None = None
    transaction_count: int
    calculated_total: Decimal
    difference: Decimal | None = None
    integrity_status: Literal["ok", "no_transactions", "difference"]
    integrity_label: str
    created_at: datetime


class CardStatementSummary(CardStatementBase):
    pass


class CardStatementDetail(CardStatementBase):
    transactions: list[TransactionRead]


class CardStatementStatusUpdate(BaseModel):
    status: Literal["open", "paid", "overdue"]
    paid_at: datetime | None = None

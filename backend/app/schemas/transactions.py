from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import TransactionStatus, TransactionType


class TransactionBase(BaseModel):
    account_id: str | None = None
    card_id: str | None = None
    card_statement_id: str | None = None
    transaction_date: str
    description: str = Field(min_length=1)
    original_description: str | None = None
    amount: Decimal
    type: TransactionType = TransactionType.expense
    category_id: str | None = None
    source_file_id: str | None = None
    installment_current: int | None = None
    installment_total: int | None = None
    status: TransactionStatus = TransactionStatus.confirmed


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    account_id: str | None = None
    card_id: str | None = None
    card_statement_id: str | None = None
    transaction_date: str | None = None
    description: str | None = None
    original_description: str | None = None
    amount: Decimal | None = None
    type: TransactionType | None = None
    category_id: str | None = None
    source_file_id: str | None = None
    installment_current: int | None = None
    installment_total: int | None = None
    status: TransactionStatus | None = None


class TransactionRead(TransactionBase):
    id: str
    user_id: str
    normalized_description: str
    created_at: datetime

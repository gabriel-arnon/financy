from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import AccountType, EntityStatus
from app.schemas.statements import CardStatementSummary
from app.schemas.transactions import TransactionRead


class AccountBase(BaseModel):
    name: str = Field(min_length=1)
    institution: str | None = None
    agency: str | None = None
    account_number: str | None = None
    type: AccountType = AccountType.checking
    balance: Decimal = Decimal("0")
    status: EntityStatus = EntityStatus.active


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    institution: str | None = None
    agency: str | None = None
    account_number: str | None = None
    type: AccountType | None = None
    balance: Decimal | None = None
    status: EntityStatus | None = None


class AccountRead(AccountBase):
    id: str
    user_id: str
    created_at: datetime


class CardBase(BaseModel):
    account_id: str | None = None
    name: str = Field(min_length=1)
    institution: str | None = None
    brand: str | None = None
    last_digits: str = Field(min_length=4, max_length=4)
    limit_amount: Decimal | None = None
    closing_day: int | None = Field(default=None, ge=1, le=31)
    due_day: int | None = Field(default=None, ge=1, le=31)
    status: EntityStatus = EntityStatus.active

    @field_validator("last_digits")
    @classmethod
    def validate_last_digits(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 4:
            raise ValueError("last_digits deve conter exatamente 4 dígitos")
        return value


class CardCreate(CardBase):
    pass


class CardUpdate(BaseModel):
    account_id: str | None = None
    name: str | None = Field(default=None, min_length=1)
    institution: str | None = None
    brand: str | None = None
    last_digits: str | None = Field(default=None, min_length=4, max_length=4)
    limit_amount: Decimal | None = None
    closing_day: int | None = Field(default=None, ge=1, le=31)
    due_day: int | None = Field(default=None, ge=1, le=31)
    status: EntityStatus | None = None

    @field_validator("last_digits")
    @classmethod
    def validate_last_digits(cls, value: str | None) -> str | None:
        if value is not None and (not value.isdigit() or len(value) != 4):
            raise ValueError("last_digits deve conter exatamente 4 dígitos")
        return value


class CardRead(CardBase):
    id: str
    user_id: str
    created_at: datetime


class AccountSummaryCard(CardRead):
    open_statement_count: int
    open_statement_total: Decimal


class AccountSummary(BaseModel):
    account: AccountRead
    cards: list[AccountSummaryCard]
    open_statements: list[CardStatementSummary]
    total_open_statements: Decimal
    total_open_statements_ok: Decimal
    total_open_statements_warning: Decimal
    transaction_count: int
    total_income: Decimal
    total_expense: Decimal
    net_balance_period: Decimal
    recent_transactions: list[TransactionRead]


class CardSummaryStatement(BaseModel):
    id: str
    reference_month: str
    due_date: str | None = None
    status: str
    reported_total: Decimal | None = None
    calculated_total: Decimal
    difference: Decimal | None = None
    integrity_status: Literal["ok", "no_transactions", "difference"]
    transaction_count: int


class CardSummaryTransaction(TransactionRead):
    pass


class CardSummary(BaseModel):
    card: CardRead
    account: AccountRead | None = None
    limit_total: Decimal | None = None
    limit_used: Decimal
    limit_available: Decimal | None = None
    usage_percent: Decimal | None = None
    upcoming_statements: list[CardSummaryStatement]
    statement_history: list[CardSummaryStatement]
    recent_transactions: list[CardSummaryTransaction]

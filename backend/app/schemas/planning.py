from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


RecurringKind = Literal["installment", "fixed_bill", "subscription"]
RecurringStatus = Literal["suggested", "active", "ignored", "inactive"]
GoalStatus = Literal["active", "completed", "paused", "inactive"]
BudgetStatus = Literal["active", "inactive"]


class RecurringItemBase(BaseModel):
    name: str = Field(min_length=1)
    kind: RecurringKind
    amount: Decimal = Decimal("0")
    cadence: str = "monthly"
    category_id: str | None = None
    account_id: str | None = None
    card_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    next_due_date: str | None = None
    status: RecurringStatus = "active"
    source: str = "manual"
    notes: str | None = None
    metadata: dict = Field(default_factory=dict)


class RecurringItemCreate(RecurringItemBase):
    pass


class RecurringItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    kind: RecurringKind | None = None
    amount: Decimal | None = None
    cadence: str | None = None
    category_id: str | None = None
    account_id: str | None = None
    card_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    next_due_date: str | None = None
    status: RecurringStatus | None = None
    source: str | None = None
    notes: str | None = None
    metadata: dict | None = None


class RecurringItemRead(RecurringItemBase):
    id: str
    user_id: str
    linked_transaction_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None


class FinancialGoalBase(BaseModel):
    name: str = Field(min_length=1)
    target_amount: Decimal
    current_amount: Decimal = Decimal("0")
    target_date: str | None = None
    status: GoalStatus = "active"
    notes: str | None = None


class FinancialGoalCreate(FinancialGoalBase):
    pass


class FinancialGoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    target_amount: Decimal | None = None
    current_amount: Decimal | None = None
    target_date: str | None = None
    status: GoalStatus | None = None
    notes: str | None = None


class FinancialGoalRead(FinancialGoalBase):
    id: str
    user_id: str
    progress_percent: Decimal
    remaining_amount: Decimal
    created_at: datetime
    updated_at: datetime | None = None


class BudgetBase(BaseModel):
    name: str = Field(min_length=1)
    amount: Decimal
    period_month: str
    category_id: str | None = None
    status: BudgetStatus = "active"
    notes: str | None = None


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    amount: Decimal | None = None
    period_month: str | None = None
    category_id: str | None = None
    status: BudgetStatus | None = None
    notes: str | None = None


class BudgetRead(BudgetBase):
    id: str
    user_id: str
    spent_amount: Decimal
    remaining_amount: Decimal
    usage_percent: Decimal
    alert_level: Literal["ok", "near_limit", "over_limit"]
    created_at: datetime
    updated_at: datetime | None = None


class PlanningOverview(BaseModel):
    recurring_items: list[RecurringItemRead]
    recurring_suggestions: list[RecurringItemRead]
    goals: list[FinancialGoalRead]
    budgets: list[BudgetRead]

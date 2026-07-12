from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import EntityStatus, ReimbursementClaimStatus, ReimbursementEventActorType, ReimbursementItemStatus


class ReimbursementContactCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    email: str | None = None
    phone: str | None = None


class ReimbursementContactUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = None
    phone: str | None = None
    status: EntityStatus | None = None


class ReimbursementContactRead(BaseModel):
    id: str
    owner_user_id: str
    display_name: str
    email: str | None = None
    phone: str | None = None
    status: EntityStatus
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime | None = None


class ReimbursementClaimCreate(BaseModel):
    contact_id: str
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    due_date: str | None = None


class ReimbursementClaimUpdate(BaseModel):
    contact_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    due_date: str | None = None


class ReimbursementItemCreate(BaseModel):
    transaction_id: str
    amount_requested: Decimal = Field(gt=0)


class ReimbursementItemUpdate(BaseModel):
    amount_requested: Decimal = Field(gt=0)


class ReimbursementItemRead(BaseModel):
    id: str
    owner_user_id: str
    claim_id: str
    transaction_id: str
    amount_requested: Decimal
    status: ReimbursementItemStatus
    transaction_snapshot: dict[str, Any]
    snapshot_is_current: bool | None = None
    position: int
    canceled_at: datetime | None = None
    created_at: datetime


class ReimbursementClaimRead(BaseModel):
    id: str
    owner_user_id: str
    contact_id: str
    title: str
    description: str | None = None
    due_date: str | None = None
    status: ReimbursementClaimStatus
    total_snapshot: Decimal | None = None
    total_amount: Decimal
    version: int
    sent_at: datetime | None = None
    canceled_at: datetime | None = None
    first_viewed_at: datetime | None = None
    last_viewed_at: datetime | None = None
    view_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None
    contact: ReimbursementContactRead | None = None
    items: list[ReimbursementItemRead] = Field(default_factory=list)


class ReimbursementEventRead(BaseModel):
    id: str
    owner_user_id: str
    claim_id: str | None = None
    contact_id: str | None = None
    item_id: str | None = None
    actor_type: ReimbursementEventActorType
    actor_user_id: str | None = None
    event_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ReimbursementOverviewRead(BaseModel):
    total_sent: Decimal
    draft_count: int
    sent_count: int
    canceled_count: int
    recent_claims: list[ReimbursementClaimRead] = Field(default_factory=list)
    draft_claims: list[ReimbursementClaimRead] = Field(default_factory=list)
    upcoming_claims: list[ReimbursementClaimRead] = Field(default_factory=list)


class ReimbursementEligibleTransactionRead(BaseModel):
    id: str
    transaction_date: str
    description: str
    amount: Decimal
    type: str
    status: str
    category_id: str | None = None
    account_id: str | None = None
    card_id: str | None = None
    card_statement_id: str | None = None
    allocated_amount: Decimal
    available_amount: Decimal
    eligible: bool
    ineligible_reason: str | None = None

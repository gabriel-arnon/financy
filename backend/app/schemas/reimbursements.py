from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.enums import (
    EntityStatus,
    ReimbursementClaimStatus,
    ReimbursementEventActorType,
    ReimbursementInvitationStatus,
    ReimbursementItemStatus,
    ReimbursementMembershipStatus,
    ReimbursementCommentAuthorRole,
)


REIMBURSEMENT_COMMENT_MAX_LENGTH = 2000


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


class ReimbursementInvitationCreate(BaseModel):
    contact_id: str
    claim_id: str | None = None
    email: str | None = None
    expires_in_days: int = Field(default=14, ge=1, le=60)


class ReimbursementInvitationRead(BaseModel):
    id: str
    owner_user_id: str
    contact_id: str
    claim_id: str | None = None
    email: str
    status: ReimbursementInvitationStatus
    expires_at: datetime
    accepted_at: datetime | None = None
    accepted_by_user_id: str | None = None
    revoked_at: datetime | None = None
    created_at: datetime
    contact: ReimbursementContactRead | None = None
    claim: ReimbursementClaimRead | None = None


class ReimbursementInvitationCreatedRead(ReimbursementInvitationRead):
    accept_token: str
    accept_path: str


class ReimbursementInvitationAccept(BaseModel):
    token: str = Field(min_length=20, max_length=256)


class ReimbursementMembershipRead(BaseModel):
    id: str
    owner_user_id: str
    contact_id: str
    auth_user_id: str
    email: str | None = None
    status: ReimbursementMembershipStatus
    linked_at: datetime
    revoked_at: datetime | None = None
    created_at: datetime
    contact: ReimbursementContactRead | None = None


class ReimbursementCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=REIMBURSEMENT_COMMENT_MAX_LENGTH)

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        body = value.strip()
        if not body:
            raise ValueError("Comentario nao pode ficar vazio.")
        return body


class ReimbursementCommentRead(BaseModel):
    id: str
    claim_id: str
    author_role: ReimbursementCommentAuthorRole
    author_label: str
    is_mine: bool
    body: str
    created_at: datetime
    updated_at: datetime | None = None


class GuestReimbursementAction(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class ReimbursementClaimAttachmentCreate(BaseModel):
    file_id: str


class ReimbursementClaimAttachmentFileRead(BaseModel):
    original_filename: str
    detected_mime_type: str
    size_bytes: int


class ReimbursementClaimAttachmentRead(BaseModel):
    id: str
    claim_id: str
    status: EntityStatus
    created_at: datetime
    deleted_at: datetime | None = None
    file: ReimbursementClaimAttachmentFileRead


class GuestReimbursementItemRead(BaseModel):
    id: str
    description: str
    transaction_date: str
    amount: Decimal
    amount_requested: Decimal
    currency: str = "BRL"


class GuestReimbursementClaimRead(BaseModel):
    id: str
    title: str
    description: str | None = None
    due_date: str | None = None
    status: ReimbursementClaimStatus
    total_amount: Decimal
    sent_at: datetime | None = None
    first_viewed_at: datetime | None = None
    last_viewed_at: datetime | None = None
    attachment_count: int = 0
    items: list[GuestReimbursementItemRead] = Field(default_factory=list)


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

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import ExcludedReason, PreviewStatus, TransactionType
from app.schemas.common import CategoryRead


class UploadImportResponse(BaseModel):
    import_id: str
    file_id: str
    filename: str
    preview_count: int


class AiImportAnalysisResponse(BaseModel):
    import_id: str
    created_preview_count: int
    skipped: bool = False


class ImportPreviewItemRead(BaseModel):
    id: str
    transaction_date: str
    description: str
    original_description: str
    amount: Decimal
    type: TransactionType
    category_id: str | None = None
    suggested_category: str | None = None
    merchant_country: str | None = None
    account_id: str | None = None
    card_id: str | None = None
    card_statement_id: str | None = None
    installment_current: int | None = None
    installment_total: int | None = None
    raw_text: str | None = None
    parser_confidence: float = 0.75
    needs_review: bool = False
    duplicate_candidate: bool = False
    default_selected: bool = True
    excluded_reason: ExcludedReason | None = None
    classification_rule_id: str | None = None
    classification_label: str | None = None
    statement_total_amount: Decimal | None = None
    statement_due_date: str | None = None
    statement_reference_month: str | None = None
    card_last_digits: str | None = None
    card_name: str | None = None
    card_brand: str | None = None
    card_institution: str | None = None
    card_limit_amount: Decimal | None = None
    account_institution: str | None = None
    account_agency: str | None = None
    account_number: str | None = None
    account_balance: Decimal | None = None
    status: PreviewStatus


class ImportPreviewResponse(BaseModel):
    import_id: str
    items: list[ImportPreviewItemRead]
    categories: list[CategoryRead]


class ConfirmPreviewItem(BaseModel):
    preview_item_id: str
    selected: bool = True
    transaction_date: str
    description: str
    amount: Decimal
    type: TransactionType
    category_id: str | None = None
    account_id: str | None = None
    card_id: str | None = None
    card_statement_id: str | None = None
    installment_current: int | None = None
    installment_total: int | None = None


class ConfirmImportRequest(BaseModel):
    items: list[ConfirmPreviewItem]


class ConfirmImportResponse(BaseModel):
    import_id: str
    created_transaction_ids: list[str]
    duplicate_preview_item_ids: list[str]
    ignored_preview_item_ids: list[str]
    confirmed_at: datetime

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import PreviewStatus, TransactionType
from app.schemas.common import CategoryRead


class UploadImportResponse(BaseModel):
    import_id: str
    file_id: str
    filename: str
    preview_count: int


class ImportPreviewItemRead(BaseModel):
    id: str
    transaction_date: str
    description: str
    original_description: str
    amount: Decimal
    type: TransactionType
    category_id: str | None = None
    account_id: str | None = None
    card_id: str | None = None
    card_statement_id: str | None = None
    installment_current: int | None = None
    installment_total: int | None = None
    raw_text: str | None = None
    parser_confidence: float
    needs_review: bool
    duplicate_candidate: bool
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

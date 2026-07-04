from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ClassificationMatchScope, EntityStatus, TransactionType


class ClassificationRuleBase(BaseModel):
    keyword: str = Field(min_length=1)
    category_id: str
    transaction_type: TransactionType | None = None
    priority: int = 100
    status: EntityStatus = EntityStatus.active
    match_scope: ClassificationMatchScope = ClassificationMatchScope.both
    auto_created: bool = False

    @field_validator("keyword")
    @classmethod
    def normalize_keyword(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("keyword nao pode ser vazio")
        return normalized


class ClassificationRuleCreate(ClassificationRuleBase):
    pass


class ClassificationRuleUpdate(BaseModel):
    keyword: str | None = Field(default=None, min_length=1)
    category_id: str | None = None
    transaction_type: TransactionType | None = None
    priority: int | None = None
    status: EntityStatus | None = None
    match_scope: ClassificationMatchScope | None = None
    auto_created: bool | None = None

    @field_validator("keyword")
    @classmethod
    def normalize_keyword(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("keyword nao pode ser vazio")
        return normalized


class ClassificationRuleRead(ClassificationRuleBase):
    id: str
    user_id: str
    created_at: datetime

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ClassificationMatchScope, EntityStatus, TransactionType
from app.services.structured_rules import ALLOWED_CONDITION_LOGIC, ALLOWED_FIELDS, ALLOWED_OPERATORS


class StructuredRuleCondition(BaseModel):
    field: str
    operator: str
    value: str | int | float | None = None

    @field_validator("field")
    @classmethod
    def validate_field(cls, value: str) -> str:
        if value not in ALLOWED_FIELDS:
            raise ValueError("campo de condicao invalido")
        return value

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, value: str) -> str:
        if value not in ALLOWED_OPERATORS:
            raise ValueError("operador de condicao invalido")
        return value


class StructuredRuleAction(BaseModel):
    type: Literal["set_category", "set_payee", "ignore_from_reports"]
    category_id: str | None = None
    payee_id: str | None = None


class ClassificationRuleBase(BaseModel):
    keyword: str = Field(min_length=1)
    category_id: str
    transaction_type: TransactionType | None = None
    priority: int = 100
    status: EntityStatus = EntityStatus.active
    match_scope: ClassificationMatchScope = ClassificationMatchScope.both
    auto_created: bool = False
    conditions: list[StructuredRuleCondition] | None = None
    condition_logic: Literal["all", "any"] = "all"
    actions: list[StructuredRuleAction] | None = None
    rule_version: int = 1

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
    conditions: list[StructuredRuleCondition] | None = None
    condition_logic: Literal["all", "any"] | None = None
    actions: list[StructuredRuleAction] | None = None
    rule_version: int | None = None

    @field_validator("condition_logic")
    @classmethod
    def validate_condition_logic(cls, value: str | None) -> str | None:
        if value is not None and value not in ALLOWED_CONDITION_LOGIC:
            raise ValueError("logica de condicao invalida")
        return value

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


class ClassificationRulePreviewSample(BaseModel):
    transaction_id: str
    transaction_date: str
    description: str
    amount: Decimal
    type: TransactionType
    current_category_id: str | None = None
    current_category_name: str | None = None
    proposed_category_id: str
    proposed_category_name: str | None = None
    already_same_category: bool


class ClassificationRulePreviewResponse(BaseModel):
    matched_count: int
    changed_count: int
    unchanged_count: int
    sample_limit: int
    samples: list[ClassificationRulePreviewSample]

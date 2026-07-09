from pydantic import BaseModel, Field


class AiFinanceInsight(BaseModel):
    title: str
    description: str
    severity: str = "info"


class AiSuggestedRule(BaseModel):
    keyword: str
    category_id: str
    category_name: str
    transaction_type: str | None = None
    match_count: int
    reason: str


class AiCategorySuggestion(BaseModel):
    transaction_id: str
    description: str
    suggested_category_id: str | None = None
    suggested_category_name: str | None = None
    reason: str


class AiRecurrenceSuggestion(BaseModel):
    description: str
    amount: str
    transaction_type: str
    occurrences: int
    cadence: str
    reason: str


class AiRenameSuggestion(BaseModel):
    transaction_id: str
    current_description: str
    suggested_description: str
    reason: str


class AiFinanceOverview(BaseModel):
    summary: str
    insights: list[AiFinanceInsight] = Field(default_factory=list)
    suggested_rules: list[AiSuggestedRule] = Field(default_factory=list)
    category_suggestions: list[AiCategorySuggestion] = Field(default_factory=list)
    recurrence_suggestions: list[AiRecurrenceSuggestion] = Field(default_factory=list)
    rename_suggestions: list[AiRenameSuggestion] = Field(default_factory=list)


class AiFinanceQuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AiFinanceQuestionSummary(BaseModel):
    matched_count: int
    total_amount: str | None = None
    currency: str = "BRL"
    period_label: str | None = None


class AiFinanceQuestionCta(BaseModel):
    label: str
    route: str
    query: dict[str, str] = Field(default_factory=dict)


class AiFinanceQuestionResponse(BaseModel):
    answer: str
    matched_count: int
    total_amount: str | None = None
    filters: list[str] = Field(default_factory=list)
    message: str | None = None
    kind: str = "transactions_summary"
    summary: AiFinanceQuestionSummary | None = None
    cta: AiFinanceQuestionCta | None = None

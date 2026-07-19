from fastapi import APIRouter, Depends

from app.api.deps import get_request_user_id, repository
from app.core.errors import AppError
from app.schemas.classification_rules import (
    ClassificationRuleCreate,
    ClassificationRulePreviewResponse,
    ClassificationRuleRead,
    ClassificationRuleUpdate,
)
from app.services.classification_rule_preview_service import ClassificationRulePreviewService


router = APIRouter(prefix="/classification-rules", tags=["classification-rules"])


def validate_category(category_id: str | None, user_id: str) -> None:
    if category_id and not repository.category_exists(category_id, user_id):
        raise AppError("Categoria da regra nao encontrada.", status_code=400, code="classification_category_not_found")


def validate_rule_categories(data: dict, user_id: str) -> None:
    validate_category(data.get("category_id"), user_id)
    for action in data.get("actions") or []:
        if action.get("type") == "set_category":
            if not action.get("category_id"):
                raise AppError("Categoria da acao da regra nao encontrada.", status_code=400, code="classification_action_category_not_found")
            validate_category(action.get("category_id"), user_id)


def ensure_rule_not_duplicate(data: dict, user_id: str, rule_id: str | None = None) -> None:
    keyword = data.get("keyword")
    if not keyword:
        return
    transaction_type = data.get("transaction_type")
    match_scope = data.get("match_scope") or "both"
    for rule in repository.list_classification_rules(user_id):
        if rule_id and rule.get("id") == rule_id:
            continue
        if (
            rule.get("status") == "active"
            and str(rule.get("keyword") or "").strip().upper() == str(keyword).strip().upper()
            and rule.get("transaction_type") == transaction_type
            and (rule.get("match_scope") or "both") == match_scope
        ):
            raise AppError("Essa regra ja existe.", status_code=409, code="classification_rule_already_exists")


@router.get("", response_model=list[ClassificationRuleRead])
def list_classification_rules(user_id: str = Depends(get_request_user_id)) -> list[ClassificationRuleRead]:
    return [ClassificationRuleRead(**item) for item in repository.list_classification_rules(user_id)]


@router.post("", response_model=ClassificationRuleRead)
def create_classification_rule(
    payload: ClassificationRuleCreate,
    user_id: str = Depends(get_request_user_id),
) -> ClassificationRuleRead:
    data = payload.model_dump(mode="json")
    validate_rule_categories(data, user_id)
    ensure_rule_not_duplicate(data, user_id)
    record = repository.create_classification_rule(user_id, data)
    return ClassificationRuleRead(**record)


@router.post("/preview", response_model=ClassificationRulePreviewResponse)
def preview_classification_rule(
    payload: ClassificationRuleCreate,
    user_id: str = Depends(get_request_user_id),
) -> ClassificationRulePreviewResponse:
    data = payload.model_dump(mode="json")
    validate_rule_categories(data, user_id)
    return ClassificationRulePreviewService(repository).preview(user_id, data)


@router.put("/{rule_id}", response_model=ClassificationRuleRead)
def update_classification_rule(
    rule_id: str,
    payload: ClassificationRuleUpdate,
    user_id: str = Depends(get_request_user_id),
) -> ClassificationRuleRead:
    data = payload.model_dump(mode="json", exclude_unset=True)
    validate_rule_categories(data, user_id)
    current = repository.get_classification_rule(user_id, rule_id)
    if not current:
        raise AppError("Regra nao encontrada.", status_code=404, code="classification_rule_not_found")
    ensure_rule_not_duplicate({**current, **data}, user_id, rule_id=rule_id)
    record = repository.update_classification_rule(user_id, rule_id, data)
    if not record:
        raise AppError("Regra nao encontrada.", status_code=404, code="classification_rule_not_found")
    return ClassificationRuleRead(**record)


@router.delete("/{rule_id}", response_model=ClassificationRuleRead)
def delete_classification_rule(rule_id: str, user_id: str = Depends(get_request_user_id)) -> ClassificationRuleRead:
    record = repository.delete_classification_rule(user_id, rule_id)
    if not record:
        raise AppError("Regra nao encontrada.", status_code=404, code="classification_rule_not_found")
    return ClassificationRuleRead(**record)

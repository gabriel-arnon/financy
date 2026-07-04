from fastapi import APIRouter, Depends

from app.api.deps import get_request_user_id, repository
from app.core.errors import AppError
from app.schemas.classification_rules import ClassificationRuleCreate, ClassificationRuleRead, ClassificationRuleUpdate


router = APIRouter(prefix="/classification-rules", tags=["classification-rules"])


def validate_category(category_id: str | None, user_id: str) -> None:
    if category_id and not repository.category_exists(category_id, user_id):
        raise AppError("Categoria da regra nao encontrada.", status_code=400, code="classification_category_not_found")


@router.get("", response_model=list[ClassificationRuleRead])
def list_classification_rules(user_id: str = Depends(get_request_user_id)) -> list[ClassificationRuleRead]:
    return [ClassificationRuleRead(**item) for item in repository.list_classification_rules(user_id)]


@router.post("", response_model=ClassificationRuleRead)
def create_classification_rule(
    payload: ClassificationRuleCreate,
    user_id: str = Depends(get_request_user_id),
) -> ClassificationRuleRead:
    validate_category(payload.category_id, user_id)
    record = repository.create_classification_rule(user_id, payload.model_dump(mode="json"))
    return ClassificationRuleRead(**record)


@router.put("/{rule_id}", response_model=ClassificationRuleRead)
def update_classification_rule(
    rule_id: str,
    payload: ClassificationRuleUpdate,
    user_id: str = Depends(get_request_user_id),
) -> ClassificationRuleRead:
    data = payload.model_dump(mode="json", exclude_unset=True)
    validate_category(data.get("category_id"), user_id)
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

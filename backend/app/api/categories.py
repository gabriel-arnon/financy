from fastapi import APIRouter, Depends

from app.api.deps import get_request_user_id, repository
from app.core.errors import AppError
from app.schemas.common import CategoryCreate, CategoryRead, CategoryUpdate


router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(user_id: str = Depends(get_request_user_id)) -> list[CategoryRead]:
    return [CategoryRead(**category) for category in repository.categories(user_id)]


@router.post("", response_model=CategoryRead)
def create_category(payload: CategoryCreate, user_id: str = Depends(get_request_user_id)) -> CategoryRead:
    record = repository.create_category(user_id, payload.model_dump(mode="json"))
    return CategoryRead(**record)


@router.put("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: str,
    payload: CategoryUpdate,
    user_id: str = Depends(get_request_user_id),
) -> CategoryRead:
    existing = repository.get_category(user_id, category_id)
    if not existing:
        raise AppError("Categoria não encontrada.", status_code=404, code="category_not_found")
    if existing.get("is_system"):
        raise AppError(
            "Categoria padrão do sistema não pode ser alterada.",
            status_code=400,
            code="category_system_protected",
        )
    record = repository.update_category(user_id, category_id, payload.model_dump(mode="json", exclude_unset=True))
    if not record:
        raise AppError("Categoria não encontrada.", status_code=404, code="category_not_found")
    return CategoryRead(**record)


@router.delete("/{category_id}", response_model=CategoryRead)
def delete_category(category_id: str, user_id: str = Depends(get_request_user_id)) -> CategoryRead:
    existing = repository.get_category(user_id, category_id)
    if not existing:
        raise AppError("Categoria não encontrada.", status_code=404, code="category_not_found")
    if existing.get("is_system"):
        raise AppError(
            "Categoria padrão do sistema não pode ser inativada.",
            status_code=400,
            code="category_system_protected",
        )
    record = repository.delete_category(user_id, category_id)
    if not record:
        raise AppError("Categoria não encontrada.", status_code=404, code="category_not_found")
    return CategoryRead(**record)

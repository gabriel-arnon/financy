from fastapi import APIRouter, Depends, Response

from app.api.deps import get_request_user_id, repository
from app.core.errors import AppError
from app.schemas.common import CategoryCreate, CategoryRead, CategoryUpdate


router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(user_id: str = Depends(get_request_user_id)) -> list[CategoryRead]:
    return [CategoryRead(**category) for category in repository.categories(user_id)]


@router.post("", response_model=CategoryRead)
def create_category(
    payload: CategoryCreate,
    response: Response,
    user_id: str = Depends(get_request_user_id),
) -> CategoryRead:
    data = payload.model_dump(mode="json")
    existing = repository.find_category_by_name(user_id, data["name"])
    if existing and existing.get("status") == "active":
        raise AppError("Essa categoria já existe.", status_code=409, code="category_already_exists")
    if existing and not existing.get("is_system"):
        record = repository.update_category(user_id, existing["id"], {**data, "status": "active"})
        response.headers["X-Financy-Category-Action"] = "reactivated"
        return CategoryRead(**record)

    record = repository.create_category(user_id, data)
    response.headers["X-Financy-Category-Action"] = "created"
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

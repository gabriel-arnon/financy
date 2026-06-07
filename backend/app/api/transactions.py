from fastapi import APIRouter, Depends

from app.api.deps import get_transaction_service, get_user_id
from app.schemas.transactions import TransactionCreate, TransactionRead, TransactionUpdate
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    user_id: str = Depends(get_user_id),
    service: TransactionService = Depends(get_transaction_service),
) -> list[TransactionRead]:
    return service.list(user_id=user_id)


@router.post("", response_model=TransactionRead)
def create_transaction(
    payload: TransactionCreate,
    user_id: str = Depends(get_user_id),
    service: TransactionService = Depends(get_transaction_service),
) -> TransactionRead:
    return service.create(user_id=user_id, payload=payload)


@router.put("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: str,
    payload: TransactionUpdate,
    user_id: str = Depends(get_user_id),
    service: TransactionService = Depends(get_transaction_service),
) -> TransactionRead:
    return service.update(user_id=user_id, transaction_id=transaction_id, payload=payload)


@router.delete("/{transaction_id}", response_model=dict[str, str])
def delete_transaction(
    transaction_id: str,
    user_id: str = Depends(get_user_id),
    service: TransactionService = Depends(get_transaction_service),
) -> dict[str, str]:
    service.delete(user_id=user_id, transaction_id=transaction_id)
    return {"status": "deleted"}

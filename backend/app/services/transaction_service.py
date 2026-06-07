from app.core.errors import AppError
from app.schemas.transactions import TransactionCreate, TransactionRead, TransactionUpdate
from app.parsers.utils import normalize_description


class TransactionService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def list(self, user_id: str) -> list[TransactionRead]:
        return [TransactionRead(**item) for item in self.repository.list_transactions(user_id)]

    def create(
        self,
        user_id: str,
        payload: TransactionCreate | None = None,
        payload_dict: dict | None = None,
        allow_duplicate: bool = True,
    ) -> TransactionRead | dict | None:
        data = payload_dict or payload.model_dump(mode="json")  # type: ignore[union-attr]
        data["original_description"] = data.get("original_description") or data["description"]
        data["normalized_description"] = normalize_description(data["description"])
        candidate = {"user_id": user_id, **data}

        if not allow_duplicate and self.repository.transaction_signature_exists(candidate):
            return None

        record = self.repository.create_transaction(user_id=user_id, payload=data)
        if payload_dict is not None:
            return record
        return TransactionRead(**record)

    def update(self, user_id: str, transaction_id: str, payload: TransactionUpdate) -> TransactionRead:
        record = self.repository.update_transaction(user_id, transaction_id, payload.model_dump(mode="json", exclude_unset=True))
        if not record:
            raise AppError("Transacao nao encontrada.", status_code=404, code="transaction_not_found")
        return TransactionRead(**record)

    def delete(self, user_id: str, transaction_id: str) -> None:
        if not self.repository.delete_transaction(user_id, transaction_id):
            raise AppError("Transacao nao encontrada.", status_code=404, code="transaction_not_found")

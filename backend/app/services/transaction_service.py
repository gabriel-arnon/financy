from calendar import monthrange
from datetime import datetime

from app.core.errors import AppError
from app.schemas.transactions import TransactionCreate, TransactionRead, TransactionUpdate
from app.parsers.utils import normalize_description


class TransactionService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def list(self, user_id: str) -> list[TransactionRead]:
        return [TransactionRead(**item) for item in self.repository.list_transactions(user_id)]

    def _validate_references(self, user_id: str, data: dict) -> None:
        if not data.get("account_id") and not data.get("card_id") and not data.get("source_file_id"):
            raise AppError("Origem da transacao e obrigatoria.", status_code=400, code="transaction_origin_required")

        account_id = data.get("account_id")
        if account_id and not self.repository.get_account(user_id, account_id):
            raise AppError("Conta da transacao nao encontrada.", status_code=400, code="transaction_account_not_found")

        card_id = data.get("card_id")
        if card_id and not self.repository.get_card(user_id, card_id):
            raise AppError("Cartao da transacao nao encontrado.", status_code=400, code="transaction_card_not_found")

        statement_id = data.get("card_statement_id")
        if statement_id and not self.repository.get_card_statement(user_id, statement_id):
            raise AppError("Fatura da transacao nao encontrada.", status_code=400, code="transaction_statement_not_found")

        category_id = data.get("category_id")
        if category_id and not self.repository.category_exists(category_id, user_id):
            raise AppError("Categoria da transacao nao encontrada.", status_code=400, code="transaction_category_not_found")

        source_file_id = data.get("source_file_id")
        get_import_file = getattr(self.repository, "get_import_file", None)
        if source_file_id and get_import_file and not get_import_file(user_id, source_file_id):
            raise AppError("Arquivo de origem da transacao nao encontrado.", status_code=400, code="transaction_source_file_not_found")

    def _date_for_statement_day(self, transaction_date: str, day: int | None) -> str | None:
        if not day:
            return None
        parsed_date = datetime.strptime(transaction_date, "%Y-%m-%d")
        last_day = monthrange(parsed_date.year, parsed_date.month)[1]
        return parsed_date.replace(day=min(day, last_day)).date().isoformat()

    def _reference_month_for_transaction(self, transaction_date: str) -> str:
        parsed_date = datetime.strptime(transaction_date, "%Y-%m-%d")
        return parsed_date.replace(day=1).date().isoformat()

    def _attach_card_statement_if_needed(self, user_id: str, data: dict) -> None:
        card_id = data.get("card_id")
        if not card_id:
            data["card_statement_id"] = None
            return
        if data.get("card_statement_id"):
            return

        card = self.repository.get_card(user_id, card_id)
        if not card:
            return
        transaction_date = data.get("transaction_date")
        if not transaction_date:
            return

        reference_month = self._reference_month_for_transaction(transaction_date)
        statement = self.repository.find_or_create_card_statement(
            user_id=user_id,
            card_id=card_id,
            reference_month=reference_month,
            due_date=self._date_for_statement_day(transaction_date, card.get("due_day")),
            closing_date=self._date_for_statement_day(transaction_date, card.get("closing_day")),
            total_amount=None,
            minimum_payment_amount=None,
            source_file_id=data.get("source_file_id"),
        )
        data["card_statement_id"] = statement["id"]

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
        self._attach_card_statement_if_needed(user_id, data)
        self._validate_references(user_id, data)
        candidate = {"user_id": user_id, **data}

        if not allow_duplicate and self.repository.transaction_signature_exists(candidate):
            return None

        record = self.repository.create_transaction(user_id=user_id, payload=data)
        if payload_dict is not None:
            return record
        return TransactionRead(**record)

    def update(self, user_id: str, transaction_id: str, payload: TransactionUpdate) -> TransactionRead:
        data = payload.model_dump(mode="json", exclude_unset=True)
        current = self.repository.get_transaction(user_id, transaction_id)
        if not current:
            raise AppError("Transacao nao encontrada.", status_code=404, code="transaction_not_found")
        if "category_id" not in payload.model_fields_set:
            description = data.get("description") or current.get("description", "")
            original_description = data.get("original_description") or current.get("original_description")
            transaction_type = data.get("type") or current.get("type")
            rule = self.repository.match_classification_rule(
                user_id,
                description,
                original_description,
                transaction_type,
                amount=data.get("amount") or current.get("amount"),
                external_source=data.get("external_source") or current.get("external_source"),
                category_id=current.get("category_id"),
            )
            if rule:
                data["category_id"] = rule["category_id"]
        merged = {**current, **data}
        self._attach_card_statement_if_needed(user_id, merged)
        data["card_statement_id"] = merged.get("card_statement_id")
        self._validate_references(user_id, merged)

        record = self.repository.update_transaction(user_id, transaction_id, data)
        if not record:
            raise AppError("Transacao nao encontrada.", status_code=404, code="transaction_not_found")
        return TransactionRead(**record)

    def delete(self, user_id: str, transaction_id: str) -> None:
        if not self.repository.delete_transaction(user_id, transaction_id):
            raise AppError("Transacao nao encontrada.", status_code=404, code="transaction_not_found")

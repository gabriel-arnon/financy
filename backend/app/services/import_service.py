from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.errors import AppError
from app.models.enums import PreviewStatus
from app.parsers.parser_factory import ParserFactory
from app.schemas.imports import ConfirmImportRequest, ConfirmImportResponse, ImportPreviewResponse, UploadImportResponse
from app.services.transaction_service import TransactionService


class ImportService:
    def __init__(self, repository, upload_dir: Path) -> None:
        self.repository = repository
        self.upload_dir = upload_dir

    async def upload(self, user_id: str, file: UploadFile) -> UploadImportResponse:
        if not file.filename:
            raise AppError("Arquivo sem nome.", code="invalid_upload")

        user_upload_dir = self.upload_dir / user_id
        user_upload_dir.mkdir(parents=True, exist_ok=True)
        storage_name = f"{uuid4()}{Path(file.filename).suffix.lower()}"
        path = user_upload_dir / storage_name
        content = await file.read()
        if not content:
            raise AppError("Arquivo vazio.", code="empty_upload")
        path.write_bytes(content)

        import_file = self.repository.create_import_file(
            {
                "user_id": user_id,
                "filename": file.filename,
                "storage_path": str(path),
                "mime_type": file.content_type,
                "size_bytes": len(content),
            }
        )
        batch = self.repository.create_import_batch(
            {
                "user_id": user_id,
                "source_file_id": import_file["id"],
                "status": "preview",
            }
        )

        parsed_result = ParserFactory.parse(path=path, filename=file.filename, mime_type=file.content_type)
        rules = self.repository.list_classification_rules(user_id)
        categories_by_id = {category["id"]: category["name"] for category in self.repository.categories(user_id)}
        parsed_items = [
            self._apply_classification_from_rules(
                item=item.model_dump(mode="json"),
                rules=rules,
                categories_by_id=categories_by_id,
            )
            for item in parsed_result.items
        ]
        self._attach_existing_detected_account(user_id, parsed_items)
        records = self.repository.create_preview_items(
            import_id=batch["id"],
            source_file_id=import_file["id"],
            user_id=user_id,
            items=parsed_items,
        )

        return UploadImportResponse(
            import_id=batch["id"],
            file_id=import_file["id"],
            filename=file.filename,
            preview_count=len(records),
        )

    def _apply_classification(self, user_id: str, item: dict) -> dict:
        rule = self.repository.match_classification_rule(
            user_id=user_id,
            description=item["description"],
            original_description=item.get("original_description"),
            transaction_type=item.get("type"),
        )
        if not rule:
            return item

        category_name = self.repository.category_name(rule["category_id"])
        item["category_id"] = rule["category_id"]
        item["classification_rule_id"] = rule["id"]
        item["classification_label"] = f"Regra: {rule['keyword']} → {category_name or 'Categoria'}"
        suggested = (item.get("suggested_category") or "").strip().lower()
        if suggested and category_name and suggested != category_name.strip().lower():
            item["needs_review"] = True
        return item

    def _apply_classification_from_rules(
        self,
        item: dict,
        rules: list[dict],
        categories_by_id: dict[str, str],
    ) -> dict:
        transaction_type = item.get("type")
        description_text = (item.get("description") or "").upper()
        original_text = (item.get("original_description") or "").upper()
        candidates: list[dict] = []

        for rule in rules:
            if rule.get("status") != "active":
                continue
            if rule.get("transaction_type") is not None and rule.get("transaction_type") != transaction_type:
                continue
            keyword = rule["keyword"].upper()
            scope = rule.get("match_scope", "both")
            haystacks = []
            if scope in ("description", "both"):
                haystacks.append(description_text)
            if scope in ("original_description", "both"):
                haystacks.append(original_text)
            if any(keyword in haystack for haystack in haystacks):
                candidates.append(rule)

        if not candidates:
            return item

        rule = sorted(candidates, key=lambda rule_item: (rule_item.get("priority", 0), rule_item.get("created_at", "")), reverse=True)[0]
        category_name = categories_by_id.get(rule["category_id"])
        item["category_id"] = rule["category_id"]
        item["classification_rule_id"] = rule["id"]
        item["classification_label"] = f"Regra: {rule['keyword']} -> {category_name or 'Categoria'}"
        suggested = (item.get("suggested_category") or "").strip().lower()
        if suggested and category_name and suggested != category_name.strip().lower():
            item["needs_review"] = True
        return item

    def get_preview(self, user_id: str, import_id: str) -> ImportPreviewResponse:
        if not self.repository.get_import_batch(user_id, import_id):
            raise AppError("Importacao nao encontrada.", status_code=404, code="import_not_found")
        items = self.repository.get_preview_items(user_id, import_id)
        return ImportPreviewResponse(import_id=import_id, items=items, categories=self.repository.categories(user_id))

    def _attach_existing_detected_account(self, user_id: str, items: list[dict]) -> None:
        item_with_account = next((item for item in items if item.get("account_agency") or item.get("account_number")), None)
        if not item_with_account:
            return

        agency = item_with_account.get("account_agency")
        account_number = item_with_account.get("account_number")
        institution = item_with_account.get("account_institution") or "Banco do Brasil"
        balance = item_with_account.get("account_balance")
        existing = None
        fallback_same_institution = None
        for account in self.repository.list_accounts(user_id):
            if agency and account_number:
                if account.get("agency") == agency and account.get("account_number") == account_number:
                    existing = account
                    break
                if (
                    not fallback_same_institution
                    and not account.get("agency")
                    and not account.get("account_number")
                    and (account.get("institution") == institution or account.get("name") == institution)
                ):
                    fallback_same_institution = account
            elif account_number and account.get("account_number") == account_number:
                existing = account
                break
        existing = existing or fallback_same_institution

        if not existing:
            return

        payload = {
            "name": institution,
            "institution": institution,
            "agency": agency,
            "account_number": account_number,
            "type": "checking",
            "balance": balance or "0",
            "status": "active",
        }
        update_payload = {
            key: value
            for key, value in payload.items()
            if value not in (None, "") and (key == "balance" or not existing.get(key))
        }
        account = self.repository.update_account(user_id, existing["id"], update_payload) or existing

        for item in items:
            if item.get("account_agency") == agency and item.get("account_number") == account_number:
                item["account_id"] = account["id"]

    def confirm(self, user_id: str, import_id: str, payload: ConfirmImportRequest) -> ConfirmImportResponse:
        if not self.repository.get_import_batch(user_id, import_id):
            raise AppError("Importacao nao encontrada.", status_code=404, code="import_not_found")

        preview_items = {item["id"]: item for item in self.repository.get_preview_items(user_id, import_id)}
        transaction_service = TransactionService(self.repository)
        created_ids: list[str] = []
        duplicates: list[str] = []
        ignored: list[str] = []

        for item in payload.items:
            stored_preview = preview_items.get(item.preview_item_id)
            if not stored_preview:
                raise AppError("Item de preview nao encontrado.", status_code=404, code="preview_item_not_found")
            if not item.selected:
                self.repository.mark_preview_status(user_id, item.preview_item_id, PreviewStatus.ignored)
                ignored.append(item.preview_item_id)
                continue

            card_statement_id = item.card_statement_id or self._statement_id_for_item(user_id, stored_preview, item)
            tx_payload = {
                **item.model_dump(exclude={"preview_item_id", "selected"}, mode="json"),
                "original_description": stored_preview.get("original_description") or item.description,
                "source_file_id": stored_preview.get("source_file_id"),
                "card_statement_id": card_statement_id,
                "status": "confirmed",
            }
            transaction = transaction_service.create(user_id=user_id, payload_dict=tx_payload, allow_duplicate=False)
            if transaction is None:
                self.repository.mark_preview_status(user_id, item.preview_item_id, PreviewStatus.duplicate)
                duplicates.append(item.preview_item_id)
            else:
                self.repository.mark_preview_status(user_id, item.preview_item_id, PreviewStatus.confirmed)
                created_ids.append(transaction["id"])

        return ConfirmImportResponse(
            import_id=import_id,
            created_transaction_ids=created_ids,
            duplicate_preview_item_ids=duplicates,
            ignored_preview_item_ids=ignored,
            confirmed_at=datetime.now(timezone.utc),
        )

    def _statement_id_for_item(self, user_id: str, stored_preview: dict, item) -> str | None:
        if item.card_statement_id:
            return item.card_statement_id
        if not item.card_id:
            return None
        reference_month = stored_preview.get("statement_reference_month")
        if not reference_month:
            return None
        statement = self.repository.find_or_create_card_statement(
            user_id=user_id,
            card_id=item.card_id,
            reference_month=reference_month,
            due_date=stored_preview.get("statement_due_date"),
            closing_date=None,
            total_amount=stored_preview.get("statement_total_amount"),
            minimum_payment_amount=None,
            source_file_id=stored_preview.get("source_file_id"),
        )
        return statement["id"]

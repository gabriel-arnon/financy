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

        self.upload_dir.mkdir(parents=True, exist_ok=True)
        storage_name = f"{uuid4()}{Path(file.filename).suffix.lower()}"
        path = self.upload_dir / storage_name
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

        parsed_items = ParserFactory.parse(path=path, filename=file.filename, mime_type=file.content_type)
        records = self.repository.create_preview_items(
            import_id=batch["id"],
            source_file_id=import_file["id"],
            user_id=user_id,
            items=[item.model_dump(mode="json") for item in parsed_items],
        )

        return UploadImportResponse(
            import_id=batch["id"],
            file_id=import_file["id"],
            filename=file.filename,
            preview_count=len(records),
        )

    def get_preview(self, user_id: str, import_id: str) -> ImportPreviewResponse:
        if not self.repository.get_import_batch(user_id, import_id):
            raise AppError("Importacao nao encontrada.", status_code=404, code="import_not_found")
        items = self.repository.get_preview_items(user_id, import_id)
        return ImportPreviewResponse(import_id=import_id, items=items, categories=self.repository.categories())

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

            tx_payload = {
                **item.model_dump(exclude={"preview_item_id", "selected"}, mode="json"),
                "original_description": stored_preview.get("original_description") or item.description,
                "source_file_id": stored_preview.get("source_file_id"),
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

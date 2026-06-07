from decimal import Decimal
from pathlib import Path

from app.models.enums import PreviewStatus, TransactionType
from app.repositories.local_json import LocalJsonRepository
from app.schemas.imports import ConfirmImportRequest, ConfirmPreviewItem
from app.services.import_service import ImportService


USER_ID = "00000000-0000-4000-8000-000000000001"


def _seed_preview(repo: LocalJsonRepository, card_statement_id: str | None = None) -> str:
    source_file = repo.create_import_file(
        {
            "user_id": USER_ID,
            "filename": "fatura.pdf",
            "storage_path": "fatura.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 10,
        }
    )
    batch = repo.create_import_batch({"user_id": USER_ID, "source_file_id": source_file["id"], "status": "preview"})
    repo.create_preview_items(
        import_id=batch["id"],
        source_file_id=source_file["id"],
        user_id=USER_ID,
        items=[
            {
                "transaction_date": "2026-05-03",
                "description": "MERCADO EXEMPLO",
                "original_description": "MERCADO EXEMPLO",
                "amount": "55.90",
                "type": TransactionType.expense.value,
                "account_id": None,
                "card_id": "11111111-1111-4111-8111-111111111111",
                "card_statement_id": card_statement_id,
                "category_id": None,
                "installment_current": None,
                "installment_total": None,
                "raw_text": "03/05 MERCADO EXEMPLO 55,90",
                "raw_row": {"line": "03/05 MERCADO EXEMPLO 55,90"},
                "parser_confidence": 0.82,
                "needs_review": False,
                "duplicate_candidate": False,
                "status": PreviewStatus.pending.value,
            }
        ],
    )
    return batch["id"]


def test_confirm_import_deduplicates_without_source_file_id(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    service = ImportService(repository=repo, upload_dir=tmp_path)
    first_import_id = _seed_preview(repo)
    second_import_id = _seed_preview(repo)

    first_item = repo.get_preview_items(USER_ID, first_import_id)[0]
    second_item = repo.get_preview_items(USER_ID, second_import_id)[0]

    first = service.confirm(
        user_id=USER_ID,
        import_id=first_import_id,
        payload=ConfirmImportRequest(
            items=[
                ConfirmPreviewItem(
                    preview_item_id=first_item["id"],
                    selected=True,
                    transaction_date="2026-05-03",
                    description="MERCADO EXEMPLO",
                    amount=Decimal("55.90"),
                    type=TransactionType.expense,
                    card_id="11111111-1111-4111-8111-111111111111",
                )
            ]
        ),
    )
    second = service.confirm(
        user_id=USER_ID,
        import_id=second_import_id,
        payload=ConfirmImportRequest(
            items=[
                ConfirmPreviewItem(
                    preview_item_id=second_item["id"],
                    selected=True,
                    transaction_date="2026-05-03",
                    description="Mercado Exemplo",
                    amount=Decimal("55.90"),
                    type=TransactionType.expense,
                    card_id="11111111-1111-4111-8111-111111111111",
                )
            ]
        ),
    )

    assert len(first.created_transaction_ids) == 1
    assert second.created_transaction_ids == []
    assert second.duplicate_preview_item_ids == [second_item["id"]]


def test_confirm_import_preserves_card_statement_id(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    statement = repo.create_card_statement(
        {
            "user_id": USER_ID,
            "card_id": "11111111-1111-4111-8111-111111111111",
            "reference_month": "2026-05-01",
            "status": "open",
        }
    )
    import_id = _seed_preview(repo, card_statement_id=statement["id"])
    item = repo.get_preview_items(USER_ID, import_id)[0]

    response = ImportService(repository=repo, upload_dir=tmp_path).confirm(
        user_id=USER_ID,
        import_id=import_id,
        payload=ConfirmImportRequest(
            items=[
                ConfirmPreviewItem(
                    preview_item_id=item["id"],
                    selected=True,
                    transaction_date="2026-05-03",
                    description="MERCADO EXEMPLO",
                    amount=Decimal("55.90"),
                    type=TransactionType.expense,
                    card_id="11111111-1111-4111-8111-111111111111",
                    card_statement_id=statement["id"],
                )
            ]
        ),
    )

    transaction = repo.list_transactions(USER_ID)[0]
    assert response.created_transaction_ids == [transaction["id"]]
    assert transaction["card_statement_id"] == statement["id"]

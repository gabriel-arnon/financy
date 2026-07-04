from decimal import Decimal
from pathlib import Path

from app.models.enums import PreviewStatus, TransactionType
from app.repositories.local_json import LocalJsonRepository
from app.schemas.imports import ConfirmImportRequest, ConfirmPreviewItem
from app.services.import_service import ImportService


USER_ID = "00000000-0000-4000-8000-000000000001"
CARD_ID = "11111111-1111-4111-8111-111111111111"


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
                "card_id": CARD_ID,
                "card_statement_id": card_statement_id,
                "category_id": None,
                "installment_current": None,
                "installment_total": None,
                "raw_text": "03/05 MERCADO EXEMPLO 55,90",
                "raw_row": {"line": "03/05 MERCADO EXEMPLO 55,90"},
                "parser_confidence": 0.82,
                "needs_review": False,
                "duplicate_candidate": False,
                "default_selected": True,
                "statement_total_amount": "55.90",
                "statement_due_date": "2026-06-10",
                "statement_reference_month": "2026-05-01",
                "card_last_digits": "1111",
                "status": PreviewStatus.pending.value,
            }
        ],
    )
    return batch["id"]


def _seed_card(repo: LocalJsonRepository) -> None:
    account = repo.create_account(
        USER_ID,
        {
            "name": "Conta Import",
            "institution": "Banco Import",
            "type": "checking",
            "balance": "0",
            "status": "active",
        },
    )
    data = repo._read()
    data["cards"].append(
        {
            "id": CARD_ID,
            "user_id": USER_ID,
            "account_id": account["id"],
            "name": "Cartao Import",
            "institution": "Banco Import",
            "brand": "Visa",
            "last_digits": "1111",
            "status": "active",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )
    repo._write(data)


def test_confirm_import_deduplicates_without_source_file_id(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    _seed_card(repo)
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
                        card_id=CARD_ID,
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
                    card_id=CARD_ID,
                )
            ]
        ),
    )

    assert len(first.created_transaction_ids) == 1
    assert second.created_transaction_ids == []
    assert second.duplicate_preview_item_ids == [second_item["id"]]


def test_confirm_import_preserves_card_statement_id(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    _seed_card(repo)
    statement = repo.create_card_statement(
        {
            "user_id": USER_ID,
            "card_id": CARD_ID,
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
                    card_id=CARD_ID,
                    card_statement_id=statement["id"],
                )
            ]
        ),
    )

    transaction = repo.list_transactions(USER_ID)[0]
    assert response.created_transaction_ids == [transaction["id"]]
    assert transaction["card_statement_id"] == statement["id"]


def test_confirm_import_creates_and_reuses_card_statement(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    _seed_card(repo)
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
                    card_id=CARD_ID,
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
                    description="MERCADO EXEMPLO",
                    amount=Decimal("55.90"),
                    type=TransactionType.expense,
                    card_id=CARD_ID,
                )
            ]
        ),
    )

    statements = repo.list_card_statements(USER_ID)
    transactions = repo.list_transactions(USER_ID)
    assert len(statements) == 1
    assert len(first.created_transaction_ids) == 1
    assert second.created_transaction_ids == []
    assert transactions[0]["card_statement_id"] == statements[0]["id"]


def test_confirm_import_reuses_card_statement_without_due_date(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    statement = repo.find_or_create_card_statement(
        user_id=USER_ID,
        card_id=CARD_ID,
        reference_month="2026-05-01",
        due_date=None,
        closing_date=None,
        total_amount="55.90",
        minimum_payment_amount=None,
        source_file_id=None,
    )
    reused = repo.find_or_create_card_statement(
        user_id=USER_ID,
        card_id=CARD_ID,
        reference_month="2026-05-01",
        due_date=None,
        closing_date=None,
        total_amount="55.90",
        minimum_payment_amount=None,
        source_file_id=None,
    )

    assert reused["id"] == statement["id"]
    assert len(repo.list_card_statements(USER_ID)) == 1


def test_import_service_does_not_create_account_from_bank_statement_metadata(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    service = ImportService(repository=repo, upload_dir=tmp_path)
    items = [
        {
            "transaction_date": "2026-05-05",
            "description": "Pix - Recebido GABRIEL ARN",
            "original_description": "Pix - Recebido GABRIEL ARN",
            "amount": "100.00",
            "type": TransactionType.income.value,
            "account_institution": "Banco do Brasil",
            "account_agency": "3970-5",
            "account_number": "29537-X",
            "account_balance": "233.26",
        }
    ]

    service._attach_existing_detected_account(USER_ID, items)

    accounts = repo.list_accounts(USER_ID)
    assert accounts == []
    assert "account_id" not in items[0]


def test_import_service_updates_existing_manual_account_from_bank_statement_metadata(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    existing = repo.create_account(
        USER_ID,
        {
            "name": "Banco do Brasil",
            "institution": "Banco do Brasil",
            "type": "checking",
            "balance": "0",
            "status": "active",
        },
    )
    items = [
        {
            "transaction_date": "2026-05-05",
            "description": "Pix - Recebido GABRIEL ARN",
            "original_description": "Pix - Recebido GABRIEL ARN",
            "amount": "100.00",
            "type": TransactionType.income.value,
            "account_institution": "Banco do Brasil",
            "account_agency": "3970-5",
            "account_number": "29537-X",
            "account_balance": "233.26",
        }
    ]

    ImportService(repository=repo, upload_dir=tmp_path)._attach_existing_detected_account(USER_ID, items)

    accounts = repo.list_accounts(USER_ID)
    assert len(accounts) == 1
    assert accounts[0]["id"] == existing["id"]
    assert accounts[0]["agency"] == "3970-5"
    assert accounts[0]["account_number"] == "29537-X"
    assert accounts[0]["balance"] == "233.26"
    assert items[0]["account_id"] == existing["id"]

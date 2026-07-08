from decimal import Decimal
from pathlib import Path

from app.models.enums import PreviewStatus, TransactionType
from app.repositories.local_json import LocalJsonRepository
from app.schemas.common import NormalizedTransactionPreview, ParserResult
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


def test_confirm_import_uses_bulk_writes_for_multiple_items(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    _seed_card(repo)
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
                "card_id": CARD_ID,
                "status": PreviewStatus.pending.value,
            },
            {
                "transaction_date": "2026-05-04",
                "description": "FARMACIA EXEMPLO",
                "original_description": "FARMACIA EXEMPLO",
                "amount": "42.10",
                "type": TransactionType.expense.value,
                "card_id": CARD_ID,
                "status": PreviewStatus.pending.value,
            },
            {
                "transaction_date": "2026-05-05",
                "description": "ITEM IGNORADO",
                "original_description": "ITEM IGNORADO",
                "amount": "10.00",
                "type": TransactionType.expense.value,
                "card_id": CARD_ID,
                "status": PreviewStatus.pending.value,
            },
        ],
    )
    preview_items = repo.get_preview_items(USER_ID, batch["id"])
    create_calls = []
    status_calls = []
    original_create_transactions = repo.create_transactions
    original_mark_preview_statuses = repo.mark_preview_statuses

    def create_transactions(user_id: str, payloads: list[dict]):
        create_calls.append(payloads)
        return original_create_transactions(user_id, payloads)

    def mark_preview_statuses(user_id: str, preview_item_ids: list[str], status: PreviewStatus):
        status_calls.append((preview_item_ids, status))
        return original_mark_preview_statuses(user_id, preview_item_ids, status)

    repo.create_transactions = create_transactions  # type: ignore[method-assign]
    repo.mark_preview_statuses = mark_preview_statuses  # type: ignore[method-assign]

    response = ImportService(repository=repo, upload_dir=tmp_path).confirm(
        user_id=USER_ID,
        import_id=batch["id"],
        payload=ConfirmImportRequest(
            items=[
                ConfirmPreviewItem(
                    preview_item_id=preview_items[0]["id"],
                    selected=True,
                    transaction_date="2026-05-03",
                    description="MERCADO EXEMPLO",
                    amount=Decimal("55.90"),
                    type=TransactionType.expense,
                    card_id=CARD_ID,
                ),
                ConfirmPreviewItem(
                    preview_item_id=preview_items[1]["id"],
                    selected=True,
                    transaction_date="2026-05-04",
                    description="FARMACIA EXEMPLO",
                    amount=Decimal("42.10"),
                    type=TransactionType.expense,
                    card_id=CARD_ID,
                ),
                ConfirmPreviewItem(
                    preview_item_id=preview_items[2]["id"],
                    selected=False,
                    transaction_date="2026-05-05",
                    description="ITEM IGNORADO",
                    amount=Decimal("10.00"),
                    type=TransactionType.expense,
                    card_id=CARD_ID,
                ),
            ]
        ),
    )

    assert len(create_calls) == 1
    assert len(create_calls[0]) == 2
    assert len(response.created_transaction_ids) == 2
    assert response.ignored_preview_item_ids == [preview_items[2]["id"]]
    assert any(call == ([preview_items[2]["id"]], PreviewStatus.ignored) for call in status_calls)
    assert any(call == ([preview_items[0]["id"], preview_items[1]["id"]], PreviewStatus.confirmed) for call in status_calls)


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


def test_import_service_attaches_existing_cards_from_detected_last_digits(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    _seed_card(repo)
    items = [
        {
            "transaction_date": "2026-05-08",
            "description": "REST CARAVELAS BERTIOGA",
            "original_description": "REST CARAVELAS BERTIOGA",
            "amount": "12.67",
            "type": TransactionType.expense.value,
            "card_last_digits": "1111",
        },
        {
            "transaction_date": "2026-05-16",
            "description": "99APP 99APP SAO PAULO",
            "original_description": "99APP 99APP SAO PAULO",
            "amount": "31.50",
            "type": TransactionType.expense.value,
            "card_last_digits": "2222",
        },
    ]

    ImportService(repository=repo, upload_dir=tmp_path)._attach_existing_detected_cards(USER_ID, items)

    assert items[0]["card_id"] == CARD_ID
    assert "card_id" not in items[1]


def test_import_service_attaches_existing_cards_from_inter_and_mercado_pago_items(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    _seed_card(repo)
    items = [
        {
            "transaction_date": "2026-06-14",
            "description": "REDE CONFIANCA",
            "original_description": "REDE CONFIANCA",
            "amount": "200.00",
            "type": TransactionType.expense.value,
            "card_last_digits": "1111",
            "raw_row": {"parser": "mercado_pago_card_statement_line_v1"},
        },
        {
            "transaction_date": "2026-05-16",
            "description": "MP *BRUNOJOSESILV",
            "original_description": "MP *BRUNOJOSESILV",
            "amount": "50.00",
            "type": TransactionType.expense.value,
            "card_last_digits": "1111",
            "raw_row": {"parser": "inter_card_statement_line_v1"},
        },
    ]

    ImportService(repository=repo, upload_dir=tmp_path)._attach_existing_detected_cards(USER_ID, items)

    assert items[0]["card_id"] == CARD_ID
    assert items[1]["card_id"] == CARD_ID


class FakeAiAnalyzer:
    enabled = True

    def analyze_pdf(self, path: Path) -> ParserResult:
        return ParserResult(
            items=[
                NormalizedTransactionPreview(
                    transaction_date="2026-07-04",
                    description="AUTO POSTO BETMAR",
                    original_description="AUTO POSTO BETMAR",
                    amount="20.00",
                    type=TransactionType.expense,
                    card_last_digits="1111",
                    parser_confidence=0.72,
                    needs_review=True,
                    default_selected=True,
                    raw_row={"parser": "ai_import_v1", "source": "ai"},
                )
            ]
        )


def test_import_service_analyze_with_ai_creates_review_preview_items(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    _seed_card(repo)
    source_path = tmp_path / "unknown.pdf"
    source_path.write_bytes(b"%PDF-1.4 fake")
    source_file = repo.create_import_file(
        {
            "user_id": USER_ID,
            "filename": "unknown.pdf",
            "storage_path": str(source_path),
            "mime_type": "application/pdf",
            "size_bytes": source_path.stat().st_size,
        }
    )
    batch = repo.create_import_batch({"user_id": USER_ID, "source_file_id": source_file["id"], "status": "preview"})

    result = ImportService(repository=repo, upload_dir=tmp_path, ai_analyzer=FakeAiAnalyzer()).analyze_with_ai(USER_ID, batch["id"])

    items = repo.get_preview_items(USER_ID, batch["id"])
    assert result.created_preview_count == 1
    assert result.skipped is False
    assert items[0]["description"] == "AUTO POSTO BETMAR"
    assert items[0]["card_id"] == CARD_ID
    assert items[0]["needs_review"] is True
    assert items[0]["raw_row"]["parser"] == "ai_import_v1"


def test_import_service_analyze_with_ai_skips_when_preview_already_has_items(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    _seed_card(repo)
    import_id = _seed_preview(repo)

    result = ImportService(repository=repo, upload_dir=tmp_path, ai_analyzer=FakeAiAnalyzer()).analyze_with_ai(USER_ID, import_id)

    assert result.created_preview_count == 0
    assert result.skipped is True

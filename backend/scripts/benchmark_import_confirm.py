from __future__ import annotations

import argparse
import sys
import tempfile
import time
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.models.enums import PreviewStatus, TransactionType
from app.repositories.local_json import LocalJsonRepository
from app.schemas.imports import ConfirmImportRequest, ConfirmPreviewItem
from app.services.import_service import ImportService


USER_ID = "00000000-0000-4000-8000-000000000001"
CARD_ID = "11111111-1111-4111-8111-111111111111"


def seed_card(repo: LocalJsonRepository) -> None:
    account = repo.create_account(
        USER_ID,
        {
            "name": "Conta Benchmark",
            "institution": "Banco Benchmark",
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
            "name": "Cartao Benchmark",
            "institution": "Banco Benchmark",
            "brand": "Visa",
            "last_digits": "1111",
            "status": "active",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )
    repo._write(data)


def seed_preview(repo: LocalJsonRepository, count: int) -> tuple[str, list[dict]]:
    source_file = repo.create_import_file(
        {
            "user_id": USER_ID,
            "filename": "benchmark.pdf",
            "storage_path": "benchmark.pdf",
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
                "transaction_date": f"2026-05-{(index % 28) + 1:02d}",
                "description": f"BENCHMARK ITEM {index:04d}",
                "original_description": f"BENCHMARK ITEM {index:04d}",
                "amount": str(Decimal("10.00") + Decimal(index) / Decimal("100")),
                "type": TransactionType.expense.value,
                "card_id": CARD_ID,
                "status": PreviewStatus.pending.value,
            }
            for index in range(count)
        ],
    )
    return batch["id"], repo.get_preview_items(USER_ID, batch["id"])


def build_payload(preview_items: list[dict]) -> ConfirmImportRequest:
    return ConfirmImportRequest(
        items=[
            ConfirmPreviewItem(
                preview_item_id=item["id"],
                selected=True,
                transaction_date=item["transaction_date"],
                description=item["description"],
                amount=Decimal(str(item["amount"])),
                type=TransactionType.expense,
                card_id=CARD_ID,
            )
            for item in preview_items
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark local da confirmacao de importacao em lote.")
    parser.add_argument("--items", type=int, default=500, help="Quantidade de itens de preview a confirmar.")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        repo = LocalJsonRepository(root)
        seed_card(repo)
        import_id, preview_items = seed_preview(repo, args.items)
        service = ImportService(repository=repo, upload_dir=root)
        payload = build_payload(preview_items)

        started_at = time.perf_counter()
        response = service.confirm(user_id=USER_ID, import_id=import_id, payload=payload)
        elapsed = time.perf_counter() - started_at

    print(f"items={args.items}")
    print(f"created={len(response.created_transaction_ids)}")
    print(f"duplicates={len(response.duplicate_preview_item_ids)}")
    print(f"ignored={len(response.ignored_preview_item_ids)}")
    print(f"elapsed_seconds={elapsed:.4f}")
    print(f"items_per_second={args.items / elapsed:.2f}")


if __name__ == "__main__":
    main()

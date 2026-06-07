import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.models.enums import PreviewStatus
from app.parsers.utils import normalize_description


DEFAULT_CATEGORIES = [
    "Alimentação",
    "Supermercado",
    "Transporte",
    "Moradia",
    "Saúde",
    "Educação",
    "Lazer",
    "Serviços",
    "Assinaturas",
    "Impostos",
    "Outros",
]


def _json_default(value: Any) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class LocalJsonRepository:
    def __init__(self, upload_dir: Path) -> None:
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.upload_dir / "local_dev_db.json"
        if not self.path.exists():
            self._write(
                {
                    "categories": [{"id": str(uuid4()), "name": name} for name in DEFAULT_CATEGORIES],
                    "import_files": [],
                    "import_batches": [],
                    "import_preview_items": [],
                    "transactions": [],
                    "card_statements": [],
                }
            )

    def _read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")

    def categories(self) -> list[dict[str, Any]]:
        return self._read()["categories"]

    def create_import_file(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        record = {"id": str(uuid4()), "created_at": datetime.now(timezone.utc).isoformat(), **payload}
        data["import_files"].append(record)
        self._write(data)
        return record

    def create_import_batch(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        record = {"id": str(uuid4()), "created_at": datetime.now(timezone.utc).isoformat(), **payload}
        data["import_batches"].append(record)
        self._write(data)
        return record

    def create_preview_items(self, import_id: str, source_file_id: str, user_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        data = self._read()
        records = []
        for item in items:
            record = {
                "id": str(uuid4()),
                "import_batch_id": import_id,
                "source_file_id": source_file_id,
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **item,
            }
            data["import_preview_items"].append(record)
            records.append(record)
        self._write(data)
        return records

    def get_preview_items(self, user_id: str, import_id: str) -> list[dict[str, Any]]:
        return [
            item
            for item in self._read()["import_preview_items"]
            if item["user_id"] == user_id and item["import_batch_id"] == import_id
        ]

    def get_import_batch(self, user_id: str, import_id: str) -> dict[str, Any] | None:
        for item in self._read()["import_batches"]:
            if item["id"] == import_id and item["user_id"] == user_id:
                return item
        return None

    def list_transactions(self, user_id: str) -> list[dict[str, Any]]:
        return [item for item in self._read()["transactions"] if item["user_id"] == user_id]

    def transaction_signature_exists(self, payload: dict[str, Any]) -> bool:
        target = self.transaction_signature(payload)
        return any(self.transaction_signature(item) == target for item in self._read()["transactions"])

    def transaction_signature(self, item: dict[str, Any]) -> tuple[Any, ...]:
        return (
            item.get("user_id"),
            item.get("account_id") or item.get("card_id"),
            item.get("transaction_date"),
            item.get("normalized_description") or normalize_description(item.get("description", "")),
            str(item.get("amount")),
            item.get("installment_current"),
            item.get("installment_total"),
        )

    def create_transaction(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        record = {
            "id": str(uuid4()),
            "user_id": user_id,
            "normalized_description": normalize_description(payload["description"]),
            "created_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        data["transactions"].append(record)
        self._write(data)
        return record

    def update_transaction(self, user_id: str, transaction_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        for index, item in enumerate(data["transactions"]):
            if item["id"] == transaction_id and item["user_id"] == user_id:
                updated = {**item, **{key: value for key, value in payload.items() if value is not None}}
                if "description" in payload and payload["description"]:
                    updated["normalized_description"] = normalize_description(payload["description"])
                data["transactions"][index] = updated
                self._write(data)
                return updated
        return None

    def delete_transaction(self, user_id: str, transaction_id: str) -> bool:
        data = self._read()
        before = len(data["transactions"])
        data["transactions"] = [
            item for item in data["transactions"] if not (item["id"] == transaction_id and item["user_id"] == user_id)
        ]
        self._write(data)
        return len(data["transactions"]) != before

    def mark_preview_status(self, user_id: str, preview_item_id: str, status: PreviewStatus) -> None:
        data = self._read()
        for item in data["import_preview_items"]:
            if item["id"] == preview_item_id and item["user_id"] == user_id:
                item["status"] = status.value
        self._write(data)

    def create_card_statement(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        record = {"id": str(uuid4()), "created_at": datetime.now(timezone.utc).isoformat(), **payload}
        data["card_statements"].append(record)
        self._write(data)
        return record

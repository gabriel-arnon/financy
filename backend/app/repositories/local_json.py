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


DEFAULT_CATEGORY_DISPLAY_NAMES = [
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

DEFAULT_CATEGORY_TYPES = {
    name: ("both" if name == "Outros" else "expense")
    for name in DEFAULT_CATEGORY_DISPLAY_NAMES
}

DEFAULT_CLASSIFICATION_SEEDS = [
    ("OPENAI", "Assinaturas"),
    ("MERCADOLIVRE", "Outros"),
    ("IFOOD", "Alimentação"),
    ("IFD", "Alimentação"),
    ("KAMPAI", "Supermercado"),
    ("POSTO", "Transporte"),
    ("ANUIDADE", "Serviços"),
]


def _json_default(value: Any) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _is_active_entity(item: dict[str, Any]) -> bool:
    return item.get("status", "active") == "active"


class LocalJsonRepository:
    def __init__(self, upload_dir: Path) -> None:
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.upload_dir / "local_dev_db.json"
        if not self.path.exists():
            now = datetime.now(timezone.utc).isoformat()
            self._write(
                {
                    "categories": [
                        {
                            "id": str(uuid4()),
                            "user_id": None,
                            "name": name,
                            "type": DEFAULT_CATEGORY_TYPES[name],
                            "status": "active",
                            "is_system": True,
                            "created_at": now,
                            "default_type_migrated": True,
                        }
                        for name in DEFAULT_CATEGORIES
                    ],
                    "accounts": [],
                    "cards": [],
                    "classification_rules": [],
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

    def categories(self, user_id: str | None = None) -> list[dict[str, Any]]:
        data = self._read()
        data.setdefault("accounts", [])
        data.setdefault("cards", [])
        data.setdefault("classification_rules", [])
        categories = data.setdefault("categories", [])
        changed = False
        now = datetime.now(timezone.utc).isoformat()
        for index, category in enumerate(categories):
            if index < len(DEFAULT_CATEGORY_DISPLAY_NAMES) and category.get("name") != DEFAULT_CATEGORY_DISPLAY_NAMES[index]:
                category["name"] = DEFAULT_CATEGORY_DISPLAY_NAMES[index]
                changed = True
            if "user_id" not in category:
                category["user_id"] = None
                changed = True
            if "is_system" not in category:
                category["is_system"] = category.get("user_id") is None and category.get("name") in DEFAULT_CATEGORY_TYPES
                changed = True
            if "type" not in category:
                category["type"] = DEFAULT_CATEGORY_TYPES.get(category.get("name", ""), "both")
                changed = True
            if (
                category.get("is_system")
                and category.get("name") in DEFAULT_CATEGORY_TYPES
                and not category.get("default_type_migrated")
            ):
                category["type"] = DEFAULT_CATEGORY_TYPES[category["name"]]
                category["default_type_migrated"] = True
                changed = True
            if "status" not in category:
                category["status"] = "active"
                changed = True
            if "created_at" not in category:
                category["created_at"] = now
                changed = True
        if changed:
            self._write(data)
        return [
            category
            for category in categories
            if _is_active_entity(category) and (user_id is None or category.get("user_id") in (None, user_id))
        ]

    def _all_categories(self, user_id: str | None = None) -> list[dict[str, Any]]:
        data = self._read()
        data.setdefault("categories", [])
        self.categories(user_id)
        data = self._read()
        return [
            category
            for category in data.setdefault("categories", [])
            if user_id is None or category.get("user_id") in (None, user_id)
        ]

    def get_category(self, user_id: str, category_id: str) -> dict[str, Any] | None:
        for category in self._all_categories(user_id):
            if category["id"] == category_id:
                return category
        return None

    def find_category_by_name(self, user_id: str, name: str) -> dict[str, Any] | None:
        normalized_name = name.strip().casefold()
        for category in self._all_categories(user_id):
            if category.get("name", "").strip().casefold() == normalized_name:
                return category
        return None

    def create_category(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        data.setdefault("categories", [])
        record = {
            "id": str(uuid4()),
            "user_id": user_id,
            "is_system": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        data["categories"].append(record)
        self._write(data)
        return record

    def update_category(self, user_id: str, category_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        data.setdefault("categories", [])
        for index, category in enumerate(data["categories"]):
            if category["id"] == category_id and category.get("user_id") in (None, user_id):
                updated = {**category, **payload}
                data["categories"][index] = updated
                self._write(data)
                return updated
        return None

    def delete_category(self, user_id: str, category_id: str) -> dict[str, Any] | None:
        return self.update_category(user_id, category_id, {"status": "inactive"})

    def _ensure_classification_seeds(self, data: dict[str, Any], user_id: str) -> bool:
        data.setdefault("classification_rules", [])
        categories_by_name = {category["name"]: category["id"] for category in self.categories()}
        existing_keywords = {
            item.get("keyword")
            for item in data["classification_rules"]
            if item.get("user_id") == user_id
        }
        now = datetime.now(timezone.utc).isoformat()
        changed = False
        for keyword, category_name in DEFAULT_CLASSIFICATION_SEEDS:
            if keyword in existing_keywords:
                continue
            category_id = categories_by_name.get(category_name)
            if not category_id:
                continue
            data["classification_rules"].append(
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "keyword": keyword,
                    "category_id": category_id,
                    "transaction_type": "expense",
                    "priority": 100,
                    "status": "active",
                    "match_scope": "both",
                    "auto_created": False,
                    "created_at": now,
                }
            )
            changed = True
        return changed

    def list_classification_rules(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        if self._ensure_classification_seeds(data, user_id):
            self._write(data)
        return [
            item
            for item in data.setdefault("classification_rules", [])
            if item["user_id"] == user_id and item.get("status") == "active"
        ]

    def _all_classification_rules(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        if self._ensure_classification_seeds(data, user_id):
            self._write(data)
        return [item for item in data.setdefault("classification_rules", []) if item["user_id"] == user_id]

    def get_classification_rule(self, user_id: str, rule_id: str) -> dict[str, Any] | None:
        for item in self._all_classification_rules(user_id):
            if item["id"] == rule_id:
                return item
        return None

    def create_classification_rule(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_classification_seeds(data, user_id)
        record = {"id": str(uuid4()), "user_id": user_id, "created_at": datetime.now(timezone.utc).isoformat(), **payload}
        data.setdefault("classification_rules", []).append(record)
        self._write(data)
        return record

    def update_classification_rule(self, user_id: str, rule_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_classification_seeds(data, user_id)
        for index, item in enumerate(data.setdefault("classification_rules", [])):
            if item["id"] == rule_id and item["user_id"] == user_id:
                updated = {**item, **payload}
                data["classification_rules"][index] = updated
                self._write(data)
                return updated
        return None

    def delete_classification_rule(self, user_id: str, rule_id: str) -> dict[str, Any] | None:
        return self.update_classification_rule(user_id, rule_id, {"status": "inactive"})

    def category_exists(self, category_id: str, user_id: str | None = None) -> bool:
        return any(category["id"] == category_id for category in self.categories(user_id))

    def category_name(self, category_id: str | None) -> str | None:
        if not category_id:
            return None
        for category in self.categories():
            if category["id"] == category_id:
                return category["name"]
        return None

    def match_classification_rule(
        self,
        user_id: str,
        description: str,
        original_description: str | None,
        transaction_type: str | None,
    ) -> dict[str, Any] | None:
        rules = [
            rule
            for rule in self.list_classification_rules(user_id)
            if rule.get("status") == "active"
            and (rule.get("transaction_type") is None or rule.get("transaction_type") == transaction_type)
        ]
        candidates: list[dict[str, Any]] = []
        description_text = description.upper()
        original_text = (original_description or "").upper()
        for rule in rules:
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
            return None
        return sorted(candidates, key=lambda item: (item.get("priority", 0), item.get("created_at", "")), reverse=True)[0]

    def list_accounts(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        return [item for item in data.setdefault("accounts", []) if item["user_id"] == user_id and _is_active_entity(item)]

    def _all_accounts(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        return [item for item in data.setdefault("accounts", []) if item["user_id"] == user_id]

    def get_account(self, user_id: str, account_id: str) -> dict[str, Any] | None:
        for item in self._all_accounts(user_id):
            if item["id"] == account_id:
                return item
        return None

    def create_account(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        data.setdefault("accounts", [])
        record = {"id": str(uuid4()), "user_id": user_id, "created_at": datetime.now(timezone.utc).isoformat(), **payload}
        data["accounts"].append(record)
        self._write(data)
        return record

    def update_account(self, user_id: str, account_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        data.setdefault("accounts", [])
        for index, item in enumerate(data["accounts"]):
            if item["id"] == account_id and item["user_id"] == user_id:
                updated = {**item, **payload}
                data["accounts"][index] = updated
                self._write(data)
                return updated
        return None

    def delete_account(self, user_id: str, account_id: str) -> dict[str, Any] | None:
        return self.update_account(user_id, account_id, {"status": "inactive"})

    def list_cards(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        return [item for item in data.setdefault("cards", []) if item["user_id"] == user_id and _is_active_entity(item)]

    def _all_cards(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        return [item for item in data.setdefault("cards", []) if item["user_id"] == user_id]

    def get_card(self, user_id: str, card_id: str) -> dict[str, Any] | None:
        for item in self._all_cards(user_id):
            if item["id"] == card_id:
                return item
        return None

    def create_card(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        data.setdefault("cards", [])
        record = {"id": str(uuid4()), "user_id": user_id, "created_at": datetime.now(timezone.utc).isoformat(), **payload}
        data["cards"].append(record)
        self._write(data)
        return record

    def update_card(self, user_id: str, card_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        data.setdefault("cards", [])
        for index, item in enumerate(data["cards"]):
            if item["id"] == card_id and item["user_id"] == user_id:
                updated = {**item, **payload}
                data["cards"][index] = updated
                self._write(data)
                return updated
        return None

    def delete_card(self, user_id: str, card_id: str) -> dict[str, Any] | None:
        return self.update_card(user_id, card_id, {"status": "inactive"})

    def create_import_file(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        record = {"id": str(uuid4()), "created_at": datetime.now(timezone.utc).isoformat(), **payload}
        data["import_files"].append(record)
        self._write(data)
        return record

    def get_import_file(self, user_id: str, source_file_id: str) -> dict[str, Any] | None:
        for item in self._read()["import_files"]:
            if item["id"] == source_file_id and item["user_id"] == user_id:
                return item
        return None

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
            if self.transaction_signature_exists(record):
                record["duplicate_candidate"] = True
                record["default_selected"] = False
                record["excluded_reason"] = "duplicate"
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

    def list_transactions_by_statement(self, user_id: str, statement_id: str) -> list[dict[str, Any]]:
        return [
            item
            for item in self._read()["transactions"]
            if item["user_id"] == user_id and item.get("card_statement_id") == statement_id
        ]

    def get_transaction(self, user_id: str, transaction_id: str) -> dict[str, Any] | None:
        for item in self.list_transactions(user_id):
            if item["id"] == transaction_id:
                return item
        return None

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

    def create_transactions(self, user_id: str, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        data = self._read()
        created_at = datetime.now(timezone.utc).isoformat()
        records = []
        for payload in payloads:
            record = {
                "id": payload.get("id") or str(uuid4()),
                "user_id": user_id,
                "normalized_description": normalize_description(payload["description"]),
                "created_at": created_at,
                **payload,
            }
            data["transactions"].append(record)
            records.append(record)
        self._write(data)
        return records

    def update_transaction(self, user_id: str, transaction_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        for index, item in enumerate(data["transactions"]):
            if item["id"] == transaction_id and item["user_id"] == user_id:
                updated = {**item, **payload}
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

    def mark_preview_statuses(self, user_id: str, preview_item_ids: list[str], status: PreviewStatus) -> None:
        if not preview_item_ids:
            return
        target_ids = set(preview_item_ids)
        data = self._read()
        for item in data["import_preview_items"]:
            if item["id"] in target_ids and item["user_id"] == user_id:
                item["status"] = status.value
        self._write(data)

    def create_card_statement(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        record = {"id": str(uuid4()), "created_at": datetime.now(timezone.utc).isoformat(), **payload}
        data["card_statements"].append(record)
        self._write(data)
        return record

    def list_card_statements(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        return [item for item in data.setdefault("card_statements", []) if item["user_id"] == user_id]

    def get_card_statement(self, user_id: str, statement_id: str) -> dict[str, Any] | None:
        for item in self.list_card_statements(user_id):
            if item["id"] == statement_id:
                return item
        return None

    def update_card_statement(self, user_id: str, statement_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        data.setdefault("card_statements", [])
        for index, item in enumerate(data["card_statements"]):
            if item["id"] == statement_id and item["user_id"] == user_id:
                updated = {**item, **payload}
                data["card_statements"][index] = updated
                self._write(data)
                return updated
        return None

    def delete_card_statement(self, user_id: str, statement_id: str) -> bool:
        data = self._read()
        data.setdefault("card_statements", [])
        before = len(data["card_statements"])
        data["card_statements"] = [
            item
            for item in data["card_statements"]
            if not (item["id"] == statement_id and item["user_id"] == user_id)
        ]
        self._write(data)
        return len(data["card_statements"]) != before

    def find_or_create_card_statement(
        self,
        *,
        user_id: str,
        card_id: str,
        reference_month: str,
        due_date: str | None,
        closing_date: str | None,
        total_amount: Any,
        minimum_payment_amount: Any,
        source_file_id: str | None,
    ) -> dict[str, Any]:
        data = self._read()
        data.setdefault("card_statements", [])
        for item in data["card_statements"]:
            if item.get("user_id") != user_id or item.get("card_id") != card_id:
                continue
            if item.get("reference_month") != reference_month:
                continue
            if due_date and item.get("due_date") != due_date:
                continue
            if not due_date:
                return item
            return item

        record = {
            "id": str(uuid4()),
            "user_id": user_id,
            "card_id": card_id,
            "reference_month": reference_month,
            "due_date": due_date,
            "closing_date": closing_date,
            "total_amount": total_amount,
            "minimum_payment_amount": minimum_payment_amount,
            "status": "open",
            "paid_at": None,
            "source_file_id": source_file_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data["card_statements"].append(record)
        self._write(data)
        return record

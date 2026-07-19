import json
from threading import RLock
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
    "Juros e dividendos",
    "Uber e apps",
    "Delivery",
    "Gasolina",
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
    "Juros e dividendos",
    "Uber e apps",
    "Delivery",
    "Gasolina",
]

DEFAULT_CATEGORY_TYPES = {
    name: ("income" if name == "Juros e dividendos" else "both" if name == "Outros" else "expense")
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
        self._lock = RLock()
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
                    "stored_files": [],
                    "transaction_attachments": [],
                    "stored_file_events": [],
                    "reimbursement_contacts": [],
                    "reimbursement_claims": [],
                    "reimbursement_items": [],
                    "reimbursement_events": [],
                    "reimbursement_invitations": [],
                    "reimbursement_memberships": [],
                    "reimbursement_claim_attachments": [],
                    "reimbursement_comments": [],
                    "reimbursement_invitation_accept_attempts": [],
                    "open_finance_items": [],
                    "open_finance_account_links": [],
                    "open_finance_transaction_links": [],
                    "open_finance_sync_runs": [],
                    "recurring_items": [],
                    "recurring_item_transactions": [],
                    "financial_goals": [],
                    "budgets": [],
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
        existing_system_names = {
            category.get("name")
            for category in categories
            if category.get("user_id") is None and category.get("is_system", True)
        }
        for name in DEFAULT_CATEGORY_DISPLAY_NAMES:
            if name in existing_system_names:
                continue
            categories.append(
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
            )
            changed = True
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

    def _ensure_planning_collections(self, data: dict[str, Any]) -> None:
        data.setdefault("recurring_items", [])
        data.setdefault("recurring_item_transactions", [])
        data.setdefault("financial_goals", [])
        data.setdefault("budgets", [])

    def list_recurring_items(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_planning_collections(data)
        return [item for item in data["recurring_items"] if item["user_id"] == user_id and item.get("status") != "inactive"]

    def create_recurring_item(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_planning_collections(data)
        now = datetime.now(timezone.utc).isoformat()
        record = {"id": payload.get("id") or str(uuid4()), "user_id": user_id, "created_at": now, "updated_at": None, **payload}
        data["recurring_items"].append(record)
        self._write(data)
        return record

    def update_recurring_item(self, user_id: str, recurring_item_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_planning_collections(data)
        for index, item in enumerate(data["recurring_items"]):
            if item["id"] == recurring_item_id and item["user_id"] == user_id:
                updated = {**item, **payload, "updated_at": datetime.now(timezone.utc).isoformat()}
                data["recurring_items"][index] = updated
                self._write(data)
                return updated
        return None

    def link_recurring_item_transaction(self, user_id: str, recurring_item_id: str, transaction_id: str) -> dict[str, Any]:
        data = self._read()
        self._ensure_planning_collections(data)
        for item in data["recurring_item_transactions"]:
            if item["user_id"] == user_id and item["recurring_item_id"] == recurring_item_id and item["transaction_id"] == transaction_id:
                return item
        record = {
            "id": str(uuid4()),
            "user_id": user_id,
            "recurring_item_id": recurring_item_id,
            "transaction_id": transaction_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data["recurring_item_transactions"].append(record)
        self._write(data)
        return record

    def count_recurring_item_transactions(self, user_id: str, recurring_item_id: str) -> int:
        data = self._read()
        self._ensure_planning_collections(data)
        return len([item for item in data["recurring_item_transactions"] if item["user_id"] == user_id and item["recurring_item_id"] == recurring_item_id])

    def list_financial_goals(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_planning_collections(data)
        return [item for item in data["financial_goals"] if item["user_id"] == user_id and item.get("status") != "inactive"]

    def create_financial_goal(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_planning_collections(data)
        now = datetime.now(timezone.utc).isoformat()
        record = {"id": payload.get("id") or str(uuid4()), "user_id": user_id, "created_at": now, "updated_at": None, **payload}
        data["financial_goals"].append(record)
        self._write(data)
        return record

    def update_financial_goal(self, user_id: str, goal_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_planning_collections(data)
        for index, item in enumerate(data["financial_goals"]):
            if item["id"] == goal_id and item["user_id"] == user_id:
                updated = {**item, **payload, "updated_at": datetime.now(timezone.utc).isoformat()}
                data["financial_goals"][index] = updated
                self._write(data)
                return updated
        return None

    def list_budgets(self, user_id: str, period_month: str | None = None) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_planning_collections(data)
        return [
            item
            for item in data["budgets"]
            if item["user_id"] == user_id
            and item.get("status") != "inactive"
            and (period_month is None or item.get("period_month") == period_month)
        ]

    def create_budget(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_planning_collections(data)
        now = datetime.now(timezone.utc).isoformat()
        record = {"id": payload.get("id") or str(uuid4()), "user_id": user_id, "created_at": now, "updated_at": None, **payload}
        data["budgets"].append(record)
        self._write(data)
        return record

    def update_budget(self, user_id: str, budget_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_planning_collections(data)
        for index, item in enumerate(data["budgets"]):
            if item["id"] == budget_id and item["user_id"] == user_id:
                updated = {**item, **payload, "updated_at": datetime.now(timezone.utc).isoformat()}
                data["budgets"][index] = updated
                self._write(data)
                return updated
        return None

    def _ensure_open_finance_collections(self, data: dict[str, Any]) -> None:
        data.setdefault("open_finance_items", [])
        data.setdefault("open_finance_account_links", [])
        data.setdefault("open_finance_transaction_links", [])
        data.setdefault("open_finance_sync_runs", [])

    def list_open_finance_items(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_open_finance_collections(data)
        return [item for item in data["open_finance_items"] if item["user_id"] == user_id]

    def get_open_finance_item_by_external_id(self, user_id: str, provider: str, external_item_id: str) -> dict[str, Any] | None:
        for item in self.list_open_finance_items(user_id):
            if item["provider"] == provider and item["external_item_id"] == external_item_id:
                return item
        return None

    def upsert_open_finance_item(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_open_finance_collections(data)
        now = datetime.now(timezone.utc).isoformat()
        provider = payload.get("provider", "pluggy")
        external_item_id = payload["external_item_id"]
        for index, item in enumerate(data["open_finance_items"]):
            if item["user_id"] == user_id and item["provider"] == provider and item["external_item_id"] == external_item_id:
                updated = {**item, **payload, "updated_at": now}
                data["open_finance_items"][index] = updated
                self._write(data)
                return updated
        record = {
            "id": payload.get("id") or str(uuid4()),
            "user_id": user_id,
            "provider": provider,
            "status": "active",
            "metadata": {},
            "created_at": now,
            "updated_at": None,
            **payload,
        }
        data["open_finance_items"].append(record)
        self._write(data)
        return record

    def upsert_open_finance_account_link(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_open_finance_collections(data)
        now = datetime.now(timezone.utc).isoformat()
        provider = payload.get("provider", "pluggy")
        external_account_id = payload["external_account_id"]
        for index, item in enumerate(data["open_finance_account_links"]):
            if item["user_id"] == user_id and item["provider"] == provider and item["external_account_id"] == external_account_id:
                updated = {**item, **payload, "updated_at": now}
                data["open_finance_account_links"][index] = updated
                self._write(data)
                return updated
        record = {
            "id": payload.get("id") or str(uuid4()),
            "user_id": user_id,
            "provider": provider,
            "metadata": {},
            "created_at": now,
            "updated_at": None,
            **payload,
        }
        data["open_finance_account_links"].append(record)
        self._write(data)
        return record

    def get_open_finance_account_link(self, user_id: str, provider: str, external_account_id: str) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_open_finance_collections(data)
        return next(
            (
                item for item in data["open_finance_account_links"]
                if item["user_id"] == user_id and item["provider"] == provider and item["external_account_id"] == external_account_id
            ),
            None,
        )

    def upsert_open_finance_transaction_link(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_open_finance_collections(data)
        now = datetime.now(timezone.utc).isoformat()
        provider = payload.get("provider", "pluggy")
        external_transaction_id = payload["external_transaction_id"]
        for index, item in enumerate(data["open_finance_transaction_links"]):
            if item["user_id"] == user_id and item["provider"] == provider and item["external_transaction_id"] == external_transaction_id:
                updated = {**item, **payload, "updated_at": now}
                data["open_finance_transaction_links"][index] = updated
                self._write(data)
                return updated
        record = {
            "id": payload.get("id") or str(uuid4()),
            "user_id": user_id,
            "provider": provider,
            "metadata": {},
            "created_at": now,
            "updated_at": None,
            **payload,
        }
        data["open_finance_transaction_links"].append(record)
        self._write(data)
        return record

    def get_open_finance_transaction_link(self, user_id: str, provider: str, external_transaction_id: str) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_open_finance_collections(data)
        return next(
            (
                item for item in data["open_finance_transaction_links"]
                if item["user_id"] == user_id and item["provider"] == provider and item["external_transaction_id"] == external_transaction_id
            ),
            None,
        )

    def create_open_finance_sync_run(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_open_finance_collections(data)
        record = {
            "id": payload.get("id") or str(uuid4()),
            "user_id": user_id,
            "provider": "pluggy",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "duration_ms": None,
            "accounts_created": 0,
            "accounts_updated": 0,
            "cards_created": 0,
            "cards_updated": 0,
            "transactions_created": 0,
            "transactions_updated": 0,
            "transactions_ignored": 0,
            "metadata": {},
            **payload,
        }
        data["open_finance_sync_runs"].append(record)
        self._write(data)
        return record

    def update_open_finance_sync_run(self, user_id: str, run_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_open_finance_collections(data)
        for index, item in enumerate(data["open_finance_sync_runs"]):
            if item["id"] == run_id and item["user_id"] == user_id:
                updated = {**item, **payload}
                data["open_finance_sync_runs"][index] = updated
                self._write(data)
                return updated
        return None

    def list_open_finance_sync_runs(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_open_finance_collections(data)
        runs = [item for item in data["open_finance_sync_runs"] if item["user_id"] == user_id]
        return sorted(runs, key=lambda item: item.get("started_at", ""), reverse=True)[:limit]

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

    def _ensure_file_collections(self, data: dict[str, Any]) -> None:
        data.setdefault("stored_files", [])
        data.setdefault("transaction_attachments", [])
        data.setdefault("stored_file_events", [])

    def create_stored_file(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_file_collections(data)
        record = {
            "id": payload.get("id") or str(uuid4()),
            "owner_user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        data["stored_files"].append(record)
        self._write(data)
        return record

    def get_stored_file(self, user_id: str, file_id: str) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_file_collections(data)
        return next((item for item in data["stored_files"] if item["id"] == file_id and item["owner_user_id"] == user_id), None)

    def update_stored_file(self, user_id: str, file_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_file_collections(data)
        for index, item in enumerate(data["stored_files"]):
            if item["id"] == file_id and item["owner_user_id"] == user_id:
                updated = {**item, **payload}
                data["stored_files"][index] = updated
                self._write(data)
                return updated
        return None

    def create_transaction_attachment(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_file_collections(data)
        existing = next(
            (
                item
                for item in data["transaction_attachments"]
                if item["owner_user_id"] == user_id
                and item["transaction_id"] == payload["transaction_id"]
                and item["file_id"] == payload["file_id"]
                and item.get("status", "active") == "active"
            ),
            None,
        )
        if existing:
            return existing
        record = {
            "id": payload.get("id") or str(uuid4()),
            "owner_user_id": user_id,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        data["transaction_attachments"].append(record)
        self._write(data)
        return record

    def list_transaction_attachments(self, user_id: str, transaction_id: str) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_file_collections(data)
        files_by_id = {item["id"]: item for item in data["stored_files"]}
        records = []
        for attachment in data["transaction_attachments"]:
            if attachment["owner_user_id"] != user_id or attachment["transaction_id"] != transaction_id:
                continue
            if attachment.get("status", "active") != "active":
                continue
            stored_file = files_by_id.get(attachment["file_id"])
            if not stored_file:
                continue
            records.append(
                {
                    **attachment,
                    "storage_bucket": stored_file.get("storage_bucket"),
                    "storage_path": stored_file.get("storage_path"),
                    "original_filename": stored_file.get("original_filename"),
                    "declared_mime_type": stored_file.get("declared_mime_type"),
                    "detected_mime_type": stored_file.get("detected_mime_type"),
                    "size_bytes": stored_file.get("size_bytes"),
                    "sha256_hash": stored_file.get("sha256_hash"),
                    "source": stored_file.get("source"),
                    "file_status": stored_file.get("status"),
                    "scan_status": stored_file.get("scan_status"),
                    "metadata": stored_file.get("metadata"),
                    "file_created_at": stored_file.get("created_at"),
                    "file_deleted_at": stored_file.get("deleted_at"),
                }
            )
        return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)

    def get_transaction_attachment(self, user_id: str, attachment_id: str) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_file_collections(data)
        return next(
            (item for item in data["transaction_attachments"] if item["id"] == attachment_id and item["owner_user_id"] == user_id),
            None,
        )

    def delete_transaction_attachment(self, user_id: str, attachment_id: str) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_file_collections(data)
        for index, item in enumerate(data["transaction_attachments"]):
            if item["id"] == attachment_id and item["owner_user_id"] == user_id:
                updated = {**item, "status": "inactive", "deleted_at": datetime.now(timezone.utc).isoformat()}
                data["transaction_attachments"][index] = updated
                self._write(data)
                return updated
        return None

    def create_stored_file_event(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_file_collections(data)
        record = {
            "id": payload.get("id") or str(uuid4()),
            "owner_user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        data["stored_file_events"].append(record)
        self._write(data)
        return record

    def list_orphan_stored_files(self, user_id: str, older_than: datetime) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_file_collections(data)
        linked_file_ids = {
            item["file_id"]
            for item in data["transaction_attachments"]
            if item["owner_user_id"] == user_id and item.get("status", "active") == "active"
        }
        records = []
        for item in data["stored_files"]:
            created_at = datetime.fromisoformat(str(item["created_at"]))
            if item["owner_user_id"] != user_id:
                continue
            if item.get("status") not in {"uploaded", "quarantined", "available"}:
                continue
            if item["id"] in linked_file_ids:
                continue
            if created_at < older_than:
                records.append(item)
        return sorted(records, key=lambda item: item.get("created_at", ""))

    def _ensure_reimbursement_collections(self, data: dict[str, Any]) -> None:
        data.setdefault("reimbursement_contacts", [])
        data.setdefault("reimbursement_claims", [])
        data.setdefault("reimbursement_items", [])
        data.setdefault("reimbursement_events", [])
        data.setdefault("reimbursement_invitations", [])
        data.setdefault("reimbursement_memberships", [])
        data.setdefault("reimbursement_claim_attachments", [])
        data.setdefault("reimbursement_comments", [])
        data.setdefault("reimbursement_invitation_accept_attempts", [])

    def list_reimbursement_contacts(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        return [item for item in data["reimbursement_contacts"] if item["owner_user_id"] == user_id]

    def get_reimbursement_contact(self, user_id: str, contact_id: str) -> dict[str, Any] | None:
        return next((item for item in self.list_reimbursement_contacts(user_id) if item["id"] == contact_id), None)

    def create_reimbursement_contact(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": payload.get("id") or str(uuid4()),
            "owner_user_id": user_id,
            "status": "active",
            "metadata": {},
            "created_at": now,
            "updated_at": now,
            **payload,
        }
        data["reimbursement_contacts"].append(record)
        self._write(data)
        return record

    def update_reimbursement_contact(self, user_id: str, contact_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        for index, item in enumerate(data["reimbursement_contacts"]):
            if item["id"] == contact_id and item["owner_user_id"] == user_id:
                updated = {**item, **payload, "updated_at": datetime.now(timezone.utc).isoformat()}
                data["reimbursement_contacts"][index] = updated
                self._write(data)
                return updated
        return None

    def list_reimbursement_claims(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        return [item for item in data["reimbursement_claims"] if item["owner_user_id"] == user_id]

    def get_reimbursement_claim(self, user_id: str, claim_id: str) -> dict[str, Any] | None:
        return next((item for item in self.list_reimbursement_claims(user_id) if item["id"] == claim_id), None)

    def create_reimbursement_claim(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": payload.get("id") or str(uuid4()),
            "owner_user_id": user_id,
            "status": "draft",
            "version": 1,
            "view_count": 0,
            "created_at": now,
            "updated_at": now,
            **payload,
        }
        data["reimbursement_claims"].append(record)
        self._write(data)
        return record

    def update_reimbursement_claim(self, user_id: str, claim_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        for index, item in enumerate(data["reimbursement_claims"]):
            if item["id"] == claim_id and item["owner_user_id"] == user_id:
                updated = {**item, **payload, "updated_at": datetime.now(timezone.utc).isoformat()}
                data["reimbursement_claims"][index] = updated
                self._write(data)
                return updated
        return None

    def list_reimbursement_items(self, user_id: str, claim_id: str | None = None) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        items = [item for item in data["reimbursement_items"] if item["owner_user_id"] == user_id]
        if claim_id:
            items = [item for item in items if item["claim_id"] == claim_id]
        return sorted(items, key=lambda item: (item.get("position", 0), item.get("created_at", "")))

    def list_reimbursement_items_by_transaction(self, user_id: str, transaction_id: str) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        canceled_claim_ids = {
            claim["id"]
            for claim in data["reimbursement_claims"]
            if claim["owner_user_id"] == user_id and claim.get("status") == "canceled"
        }
        return [
            item
            for item in data["reimbursement_items"]
            if item["owner_user_id"] == user_id
            and item["transaction_id"] == transaction_id
            and item.get("status") == "active"
            and item.get("claim_id") not in canceled_claim_ids
        ]

    def get_reimbursement_item(self, user_id: str, item_id: str) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        return next((item for item in data["reimbursement_items"] if item["id"] == item_id and item["owner_user_id"] == user_id), None)

    def create_reimbursement_item(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        record = {
            "id": payload.get("id") or str(uuid4()),
            "owner_user_id": user_id,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        data["reimbursement_items"].append(record)
        self._write(data)
        return record

    def update_reimbursement_item(self, user_id: str, item_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        for index, item in enumerate(data["reimbursement_items"]):
            if item["id"] == item_id and item["owner_user_id"] == user_id:
                updated = {**item, **payload}
                data["reimbursement_items"][index] = updated
                self._write(data)
                return updated
        return None

    def _active_reimbursement_allocation(
        self,
        data: dict[str, Any],
        user_id: str,
        transaction_id: str,
        excluding_item_id: str | None = None,
    ) -> Decimal:
        canceled_claim_ids = {
            claim["id"]
            for claim in data["reimbursement_claims"]
            if claim["owner_user_id"] == user_id and claim.get("status") == "canceled"
        }
        total = Decimal("0.00")
        for item in data["reimbursement_items"]:
            if item["owner_user_id"] != user_id or item["transaction_id"] != transaction_id:
                continue
            if item.get("status") != "active" or item.get("claim_id") in canceled_claim_ids:
                continue
            if excluding_item_id and item["id"] == excluding_item_id:
                continue
            total += Decimal(str(item["amount_requested"]))
        return total.quantize(Decimal("0.01"))

    def _transaction_reimbursable_amount(self, transaction: dict[str, Any]) -> Decimal:
        return abs(Decimal(str(transaction["amount"]))).quantize(Decimal("0.01"))

    def create_reimbursement_item_with_allocation(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            self._ensure_reimbursement_collections(data)
            transaction = next(
                (item for item in data["transactions"] if item["id"] == payload["transaction_id"] and item["user_id"] == user_id),
                None,
            )
            if not transaction:
                return {"error": "transaction_not_found"}
            if transaction.get("type") != "expense" or Decimal(str(transaction.get("amount", "0"))) == Decimal("0"):
                return {"error": "transaction_not_reimbursable"}
            duplicate = next(
                (
                    item
                    for item in data["reimbursement_items"]
                    if item["owner_user_id"] == user_id
                    and item["claim_id"] == payload["claim_id"]
                    and item["transaction_id"] == payload["transaction_id"]
                    and item.get("status") == "active"
                ),
                None,
            )
            if duplicate:
                return {"error": "reimbursement_item_duplicate"}
            requested = Decimal(str(payload["amount_requested"])).quantize(Decimal("0.01"))
            allocated = self._active_reimbursement_allocation(data, user_id, transaction["id"])
            if allocated + requested > self._transaction_reimbursable_amount(transaction):
                return {"error": "reimbursement_amount_exceeds_transaction"}
            record = {
                "id": payload.get("id") or str(uuid4()),
                "owner_user_id": user_id,
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
                **payload,
            }
            data["reimbursement_items"].append(record)
            self._write(data)
            return {"item": record}

    def update_reimbursement_item_with_allocation(self, user_id: str, item_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            self._ensure_reimbursement_collections(data)
            item_index = next(
                (
                    index
                    for index, item in enumerate(data["reimbursement_items"])
                    if item["id"] == item_id and item["owner_user_id"] == user_id
                ),
                None,
            )
            if item_index is None:
                return {"error": "reimbursement_item_not_found"}
            current = data["reimbursement_items"][item_index]
            transaction = next(
                (item for item in data["transactions"] if item["id"] == current["transaction_id"] and item["user_id"] == user_id),
                None,
            )
            if not transaction:
                return {"error": "transaction_not_found"}
            if transaction.get("type") != "expense" or Decimal(str(transaction.get("amount", "0"))) == Decimal("0"):
                return {"error": "transaction_not_reimbursable"}
            requested = Decimal(str(payload["amount_requested"])).quantize(Decimal("0.01"))
            allocated = self._active_reimbursement_allocation(data, user_id, transaction["id"], excluding_item_id=item_id)
            if allocated + requested > self._transaction_reimbursable_amount(transaction):
                return {"error": "reimbursement_amount_exceeds_transaction"}
            updated = {**current, **payload}
            data["reimbursement_items"][item_index] = updated
            self._write(data)
            return {"item": updated}

    def create_reimbursement_event(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        record = {
            "id": payload.get("id") or str(uuid4()),
            "owner_user_id": user_id,
            "actor_type": "owner",
            "actor_user_id": user_id,
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        data["reimbursement_events"].append(record)
        self._write(data)
        return record

    def list_reimbursement_events(self, user_id: str, claim_id: str) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        return [
            item
            for item in sorted(data["reimbursement_events"], key=lambda item: item.get("created_at", ""))
            if item["owner_user_id"] == user_id and item.get("claim_id") == claim_id
        ]

    def create_reimbursement_comment(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        record = {
            "id": payload.get("id") or str(uuid4()),
            "owner_user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": None,
            "deleted_at": None,
            "deleted_by_user_id": None,
            "deleted_by_role": None,
            **payload,
        }
        data["reimbursement_comments"].append(record)
        self._write(data)
        return record

    def list_reimbursement_comments(self, user_id: str, claim_id: str, limit: int = 50, cursor: str | None = None) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        comments = [
            item
            for item in data["reimbursement_comments"]
            if item["owner_user_id"] == user_id and item["claim_id"] == claim_id and not item.get("deleted_at")
        ]
        comments = sorted(comments, key=lambda item: (item.get("created_at", ""), item.get("id", "")))
        if cursor:
            comments = [item for item in comments if f"{item.get('created_at', '')}|{item.get('id', '')}" > cursor]
        return comments[:limit]

    def get_reimbursement_comment(self, user_id: str, comment_id: str) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        return next(
            (item for item in data["reimbursement_comments"] if item["id"] == comment_id and item["owner_user_id"] == user_id),
            None,
        )

    def update_reimbursement_comment(self, user_id: str, comment_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        for index, item in enumerate(data["reimbursement_comments"]):
            if item["id"] == comment_id and item["owner_user_id"] == user_id:
                updated = {**item, **payload}
                data["reimbursement_comments"][index] = updated
                self._write(data)
                return updated
        return None

    def list_reimbursement_invitations(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        return [item for item in data["reimbursement_invitations"] if item["owner_user_id"] == user_id]

    def get_reimbursement_invitation(self, user_id: str, invitation_id: str) -> dict[str, Any] | None:
        return next((item for item in self.list_reimbursement_invitations(user_id) if item["id"] == invitation_id), None)

    def get_reimbursement_invitation_by_token_hash(self, token_hash: str) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        return next((item for item in data["reimbursement_invitations"] if item["token_hash"] == token_hash), None)

    def begin_invitation_accept_attempt(
        self,
        *,
        token_hash: str,
        ip_hash: str,
        auth_user_id: str,
        max_attempts: int,
        window_started_at: datetime,
        attempted_at: datetime,
    ) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            self._ensure_reimbursement_collections(data)
            window_iso = window_started_at.isoformat()
            recent = [
                item
                for item in data["reimbursement_invitation_accept_attempts"]
                if item["token_hash"] == token_hash
                and item["ip_hash"] == ip_hash
                and item.get("attempted_at", "") >= window_iso
            ]
            allowed = len(recent) < max_attempts
            record = {
                "id": str(uuid4()),
                "token_hash": token_hash,
                "ip_hash": ip_hash,
                "auth_user_id": auth_user_id,
                "attempted_at": attempted_at.isoformat(),
                "success": False,
                "failure_code": None if allowed else "rate_limited",
            }
            data["reimbursement_invitation_accept_attempts"].append(record)
            self._write(data)
            return {"allowed": allowed, "attempt_id": record["id"]}

    def complete_invitation_accept_attempt(self, attempt_id: str, *, success: bool, failure_code: str | None) -> None:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        for index, item in enumerate(data["reimbursement_invitation_accept_attempts"]):
            if item["id"] == attempt_id:
                data["reimbursement_invitation_accept_attempts"][index] = {**item, "success": success, "failure_code": failure_code}
                self._write(data)
                return

    def create_reimbursement_invitation(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        record = {
            "id": payload.get("id") or str(uuid4()),
            "owner_user_id": user_id,
            **payload,
        }
        data["reimbursement_invitations"].append(record)
        self._write(data)
        return record

    def update_reimbursement_invitation(self, user_id: str, invitation_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        for index, item in enumerate(data["reimbursement_invitations"]):
            if item["id"] == invitation_id and item["owner_user_id"] == user_id:
                updated = {**item, **payload}
                data["reimbursement_invitations"][index] = updated
                self._write(data)
                return updated
        return None

    def list_reimbursement_memberships(self, user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        return [item for item in data["reimbursement_memberships"] if item["owner_user_id"] == user_id]

    def get_reimbursement_membership(self, user_id: str, membership_id: str) -> dict[str, Any] | None:
        return next((item for item in self.list_reimbursement_memberships(user_id) if item["id"] == membership_id), None)

    def get_active_reimbursement_membership(self, user_id: str, contact_id: str, auth_user_id: str) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        return next(
            (
                item for item in data["reimbursement_memberships"]
                if item["owner_user_id"] == user_id
                and item["contact_id"] == contact_id
                and item["auth_user_id"] == auth_user_id
                and item.get("status") == "active"
            ),
            None,
        )

    def create_reimbursement_membership(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        record = {
            "id": payload.get("id") or str(uuid4()),
            "owner_user_id": user_id,
            **payload,
        }
        data["reimbursement_memberships"].append(record)
        self._write(data)
        return record

    def update_reimbursement_membership(self, user_id: str, membership_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        for index, item in enumerate(data["reimbursement_memberships"]):
            if item["id"] == membership_id and item["owner_user_id"] == user_id:
                updated = {**item, **payload}
                data["reimbursement_memberships"][index] = updated
                self._write(data)
                return updated
        return None

    def list_guest_reimbursement_claims(self, guest_user_id: str) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        active_contact_ids = {
            item["contact_id"]
            for item in data["reimbursement_memberships"]
            if item["auth_user_id"] == guest_user_id and item.get("status") == "active"
        }
        allowed_statuses = {"sent", "acknowledged", "disputed", "partially_paid", "paid", "canceled"}
        return [
            item
            for item in sorted(data["reimbursement_claims"], key=lambda claim: claim.get("created_at", ""), reverse=True)
            if item.get("contact_id") in active_contact_ids and item.get("status") in allowed_statuses
        ]

    def get_guest_reimbursement_claim(self, guest_user_id: str, claim_id: str) -> dict[str, Any] | None:
        return next((item for item in self.list_guest_reimbursement_claims(guest_user_id) if item["id"] == claim_id), None)

    def create_reimbursement_claim_attachment(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        existing = next(
            (
                item for item in data["reimbursement_claim_attachments"]
                if item["owner_user_id"] == user_id
                and item["claim_id"] == payload["claim_id"]
                and item["file_id"] == payload["file_id"]
                and item.get("status", "active") == "active"
            ),
            None,
        )
        if existing:
            return existing
        record = {
            "id": payload.get("id") or str(uuid4()),
            "owner_user_id": user_id,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        data["reimbursement_claim_attachments"].append(record)
        self._write(data)
        return record

    def list_reimbursement_claim_attachments(self, user_id: str, claim_id: str) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        return [
            item for item in data["reimbursement_claim_attachments"]
            if item["owner_user_id"] == user_id and item["claim_id"] == claim_id and item.get("status", "active") == "active"
        ]

    def get_reimbursement_claim_attachment(self, user_id: str, attachment_id: str) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        return next(
            (item for item in data["reimbursement_claim_attachments"] if item["id"] == attachment_id and item["owner_user_id"] == user_id),
            None,
        )

    def update_reimbursement_claim_attachment(self, user_id: str, attachment_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        for index, item in enumerate(data["reimbursement_claim_attachments"]):
            if item["id"] == attachment_id and item["owner_user_id"] == user_id:
                updated = {**item, **payload}
                data["reimbursement_claim_attachments"][index] = updated
                self._write(data)
                return updated
        return None

    def list_reimbursement_candidate_transactions(self, user_id: str, query: str | None = None, limit: int = 30) -> list[dict[str, Any]]:
        data = self._read()
        self._ensure_reimbursement_collections(data)
        normalized_query = (query or "").strip().lower()
        records = []
        for transaction in sorted(data["transactions"], key=lambda item: item.get("transaction_date", ""), reverse=True):
            if transaction["user_id"] != user_id:
                continue
            if normalized_query and normalized_query not in transaction.get("description", "").lower():
                continue
            allocated = self._active_reimbursement_allocation(data, user_id, transaction["id"])
            records.append({**transaction, "allocated_amount": str(allocated)})
            if len(records) >= limit:
                break
        return records

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.models.enums import PreviewStatus
from app.parsers.utils import normalize_description
from app.repositories.local_json import DEFAULT_CLASSIFICATION_SEEDS


SYSTEM_USER_EMAIL = "dev@financy.local"


def _adapt(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (dict, list)):
        return Jsonb(value)
    return value


def _normalize_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    return value


def _record(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: _normalize_value(value) for key, value in row.items()}


def _records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_record(row) or {} for row in rows]


class PostgresRepository:
    def __init__(self, database_url: str, dev_user_id: str) -> None:
        self.database_url = database_url
        self.dev_user_id = dev_user_id
        self.pool = ConnectionPool(
            database_url,
            kwargs={"row_factory": dict_row},
            min_size=1,
            max_size=5,
            open=True,
        )
        self._ensure_profile(dev_user_id)

    def _connect(self):
        return self.pool.connection()

    def ensure_profile(self, user_id: str, email: str | None = None, full_name: str | None = None) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into profiles (id, email, full_name)
                values (%s, %s, %s)
                on conflict (id) do update set
                  email = coalesce(excluded.email, profiles.email),
                  full_name = coalesce(excluded.full_name, profiles.full_name)
                """,
                (user_id, email, full_name),
            )

    def _ensure_profile(self, user_id: str) -> None:
        self.ensure_profile(user_id, email=SYSTEM_USER_EMAIL, full_name="Local Dev")

    def _fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            return _records(cur.fetchall())

    def _fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, params)
            return _record(cur.fetchone())

    def _execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, params)

    def _insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = {key: value for key, value in payload.items() if value is not None}
        columns = list(data.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        names = ", ".join(columns)
        values = tuple(_adapt(data[column]) for column in columns)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(f"insert into {table} ({names}) values ({placeholders}) returning *", values)
            return _record(cur.fetchone()) or {}

    def _update(
        self,
        table: str,
        payload: dict[str, Any],
        where: str,
        params: tuple[Any, ...],
    ) -> dict[str, Any] | None:
        if not payload:
            return self._fetch_one(f"select * from {table} where {where}", params)
        columns = list(payload.keys())
        assignments = ", ".join(f"{column} = %s" for column in columns)
        values = tuple(_adapt(payload[column]) for column in columns)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"update {table} set {assignments} where {where} returning *",
                values + params,
            )
            return _record(cur.fetchone())

    def categories(self, user_id: str | None = None) -> list[dict[str, Any]]:
        if user_id is None:
            return self._fetch_all(
                "select * from categories where status = 'active' order by is_system desc, name"
            )
        return self._fetch_all(
            """
            select * from categories
            where status = 'active' and (user_id is null or user_id = %s)
            order by is_system desc, name
            """,
            (user_id,),
        )

    def _all_categories(self, user_id: str | None = None) -> list[dict[str, Any]]:
        if user_id is None:
            return self._fetch_all("select * from categories order by is_system desc, name")
        return self._fetch_all(
            "select * from categories where user_id is null or user_id = %s order by is_system desc, name",
            (user_id,),
        )

    def get_category(self, user_id: str, category_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            "select * from categories where id = %s and (user_id is null or user_id = %s)",
            (category_id, user_id),
        )

    def create_category(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        return self._insert(
            "categories",
            {
                "id": payload.get("id") or str(uuid4()),
                "user_id": user_id,
                "is_system": False,
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def update_category(self, user_id: str, category_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update(
            "categories",
            payload,
            "id = %s and (user_id is null or user_id = %s)",
            (category_id, user_id),
        )

    def delete_category(self, user_id: str, category_id: str) -> dict[str, Any] | None:
        return self.update_category(user_id, category_id, {"status": "inactive"})

    def _ensure_classification_seeds(self, user_id: str) -> None:
        categories_by_name = {category["name"]: category["id"] for category in self.categories()}
        existing = {
            item["keyword"]
            for item in self._fetch_all("select keyword from classification_rules where user_id = %s", (user_id,))
        }
        for keyword, category_name in DEFAULT_CLASSIFICATION_SEEDS:
            category_id = categories_by_name.get(category_name)
            if not category_id or keyword in existing:
                continue
            self.create_classification_rule(
                user_id,
                {
                    "keyword": keyword,
                    "category_id": category_id,
                    "transaction_type": "expense",
                    "priority": 100,
                    "status": "active",
                    "match_scope": "both",
                    "auto_created": False,
                },
            )

    def list_classification_rules(self, user_id: str) -> list[dict[str, Any]]:
        self._ensure_classification_seeds(user_id)
        return self._fetch_all(
            "select * from classification_rules where user_id = %s and status = 'active' order by priority desc, created_at desc",
            (user_id,),
        )

    def _all_classification_rules(self, user_id: str) -> list[dict[str, Any]]:
        self._ensure_classification_seeds(user_id)
        return self._fetch_all(
            "select * from classification_rules where user_id = %s order by priority desc, created_at desc",
            (user_id,),
        )

    def get_classification_rule(self, user_id: str, rule_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            "select * from classification_rules where id = %s and user_id = %s",
            (rule_id, user_id),
        )

    def create_classification_rule(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        return self._insert(
            "classification_rules",
            {
                "id": payload.get("id") or str(uuid4()),
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def update_classification_rule(self, user_id: str, rule_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update(
            "classification_rules",
            payload,
            "id = %s and user_id = %s",
            (rule_id, user_id),
        )

    def delete_classification_rule(self, user_id: str, rule_id: str) -> dict[str, Any] | None:
        return self.update_classification_rule(user_id, rule_id, {"status": "inactive"})

    def category_exists(self, category_id: str, user_id: str | None = None) -> bool:
        if user_id is None:
            result = self._fetch_one("select 1 as exists from categories where id = %s and status = 'active'", (category_id,))
        else:
            result = self._fetch_one(
                "select 1 as exists from categories where id = %s and status = 'active' and (user_id is null or user_id = %s)",
                (category_id, user_id),
            )
        return result is not None

    def category_name(self, category_id: str | None) -> str | None:
        if not category_id:
            return None
        item = self._fetch_one("select name from categories where id = %s and status = 'active'", (category_id,))
        return item["name"] if item else None

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
        return self._fetch_all(
            "select * from accounts where user_id = %s and status = 'active' order by created_at desc",
            (user_id,),
        )

    def _all_accounts(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all("select * from accounts where user_id = %s order by created_at desc", (user_id,))

    def get_account(self, user_id: str, account_id: str) -> dict[str, Any] | None:
        return self._fetch_one("select * from accounts where id = %s and user_id = %s", (account_id, user_id))

    def create_account(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        return self._insert(
            "accounts",
            {
                "id": payload.get("id") or str(uuid4()),
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def update_account(self, user_id: str, account_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update("accounts", payload, "id = %s and user_id = %s", (account_id, user_id))

    def delete_account(self, user_id: str, account_id: str) -> dict[str, Any] | None:
        return self.update_account(user_id, account_id, {"status": "inactive"})

    def list_cards(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            "select * from cards where user_id = %s and status = 'active' order by created_at desc",
            (user_id,),
        )

    def _all_cards(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all("select * from cards where user_id = %s order by created_at desc", (user_id,))

    def get_card(self, user_id: str, card_id: str) -> dict[str, Any] | None:
        return self._fetch_one("select * from cards where id = %s and user_id = %s", (card_id, user_id))

    def create_card(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        return self._insert(
            "cards",
            {
                "id": payload.get("id") or str(uuid4()),
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def update_card(self, user_id: str, card_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update("cards", payload, "id = %s and user_id = %s", (card_id, user_id))

    def delete_card(self, user_id: str, card_id: str) -> dict[str, Any] | None:
        return self.update_card(user_id, card_id, {"status": "inactive"})

    def create_import_file(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("user_id"):
            self._ensure_profile(payload["user_id"])
        return self._insert(
            "import_files",
            {
                "id": payload.get("id") or str(uuid4()),
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def get_import_file(self, user_id: str, source_file_id: str) -> dict[str, Any] | None:
        return self._fetch_one("select * from import_files where id = %s and user_id = %s", (source_file_id, user_id))

    def create_import_batch(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("user_id"):
            self._ensure_profile(payload["user_id"])
        return self._insert(
            "import_batches",
            {
                "id": payload.get("id") or str(uuid4()),
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def create_preview_items(
        self,
        import_id: str,
        source_file_id: str,
        user_id: str,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        self._ensure_profile(user_id)
        records = []
        existing_signatures = {self.transaction_signature(item) for item in self.list_transactions(user_id)}
        with self._connect() as conn:
            for item in items:
                record = {
                    "id": item.get("id") or str(uuid4()),
                    "import_batch_id": import_id,
                    "source_file_id": source_file_id,
                    "user_id": user_id,
                    "created_at": datetime.now(timezone.utc),
                    **item,
                }
                if self.transaction_signature(record) in existing_signatures:
                    record["duplicate_candidate"] = True
                    record["default_selected"] = False
                    record["excluded_reason"] = "duplicate"
                columns = list(record.keys())
                placeholders = ", ".join(["%s"] * len(columns))
                names = ", ".join(columns)
                values = tuple(_adapt(record[column]) for column in columns)
                with conn.cursor() as cur:
                    cur.execute(
                        f"insert into import_preview_items ({names}) values ({placeholders}) returning *",
                        values,
                    )
                    records.append(_record(cur.fetchone()) or {})
        return records

    def get_preview_items(self, user_id: str, import_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select * from import_preview_items
            where user_id = %s and import_batch_id = %s
            order by transaction_date, created_at
            """,
            (user_id, import_id),
        )

    def get_import_batch(self, user_id: str, import_id: str) -> dict[str, Any] | None:
        return self._fetch_one("select * from import_batches where id = %s and user_id = %s", (import_id, user_id))

    def list_transactions(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            "select * from transactions where user_id = %s order by transaction_date desc, created_at desc",
            (user_id,),
        )

    def list_transactions_by_statement(self, user_id: str, statement_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select * from transactions
            where user_id = %s and card_statement_id = %s
            order by transaction_date desc, created_at desc
            """,
            (user_id, statement_id),
        )

    def get_transaction(self, user_id: str, transaction_id: str) -> dict[str, Any] | None:
        return self._fetch_one("select * from transactions where id = %s and user_id = %s", (transaction_id, user_id))

    def transaction_signature_exists(self, payload: dict[str, Any]) -> bool:
        target = self.transaction_signature(payload)
        return any(self.transaction_signature(item) == target for item in self.list_transactions(payload["user_id"]))

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
        self._ensure_profile(user_id)
        record = {
            "id": payload.get("id") or str(uuid4()),
            "user_id": user_id,
            "normalized_description": normalize_description(payload["description"]),
            "created_at": datetime.now(timezone.utc),
            **payload,
        }
        return self._insert("transactions", record)

    def update_transaction(self, user_id: str, transaction_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = dict(payload)
        if "description" in data and data["description"]:
            data["normalized_description"] = normalize_description(data["description"])
        return self._update("transactions", data, "id = %s and user_id = %s", (transaction_id, user_id))

    def delete_transaction(self, user_id: str, transaction_id: str) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("delete from transactions where id = %s and user_id = %s", (transaction_id, user_id))
            return cur.rowcount > 0

    def mark_preview_status(self, user_id: str, preview_item_id: str, status: PreviewStatus) -> None:
        self._execute(
            "update import_preview_items set status = %s where id = %s and user_id = %s",
            (status.value, preview_item_id, user_id),
        )

    def create_card_statement(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = dict(payload)
        if data.get("user_id"):
            self._ensure_profile(data["user_id"])
        if "reported_total" in data and "total_amount" not in data:
            data["total_amount"] = data.pop("reported_total")
        return self._insert(
            "card_statements",
            {
                "id": data.get("id") or str(uuid4()),
                "created_at": datetime.now(timezone.utc),
                **data,
            },
        )

    def list_card_statements(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            "select * from card_statements where user_id = %s order by reference_month desc, created_at desc",
            (user_id,),
        )

    def get_card_statement(self, user_id: str, statement_id: str) -> dict[str, Any] | None:
        return self._fetch_one("select * from card_statements where id = %s and user_id = %s", (statement_id, user_id))

    def update_card_statement(self, user_id: str, statement_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = dict(payload)
        if "reported_total" in data and "total_amount" not in data:
            data["total_amount"] = data.pop("reported_total")
        return self._update("card_statements", data, "id = %s and user_id = %s", (statement_id, user_id))

    def delete_card_statement(self, user_id: str, statement_id: str) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("delete from card_statements where id = %s and user_id = %s", (statement_id, user_id))
            return cur.rowcount > 0

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
        params: tuple[Any, ...]
        if due_date:
            where = "user_id = %s and card_id = %s and reference_month = %s and due_date = %s"
            params = (user_id, card_id, reference_month, due_date)
        else:
            where = "user_id = %s and card_id = %s and reference_month = %s"
            params = (user_id, card_id, reference_month)
        existing = self._fetch_one(f"select * from card_statements where {where} order by created_at desc limit 1", params)
        if existing:
            return existing
        return self.create_card_statement(
            {
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
            }
        )

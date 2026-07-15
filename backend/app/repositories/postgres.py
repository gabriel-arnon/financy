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

    def find_category_by_name(self, user_id: str, name: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            select * from categories
            where lower(trim(name)) = lower(trim(%s)) and (user_id is null or user_id = %s)
            order by is_system desc, status = 'active' desc, created_at desc
            limit 1
            """,
            (name, user_id),
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

    def list_open_finance_items(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            "select * from open_finance_items where user_id = %s order by created_at desc",
            (user_id,),
        )

    def get_open_finance_item_by_external_id(self, user_id: str, provider: str, external_item_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            select * from open_finance_items
            where user_id = %s and provider = %s and external_item_id = %s
            """,
            (user_id, provider, external_item_id),
        )

    def upsert_open_finance_item(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        record = {
            "id": payload.get("id") or str(uuid4()),
            "user_id": user_id,
            "provider": payload.get("provider", "pluggy"),
            "status": "active",
            "metadata": {},
            "created_at": datetime.now(timezone.utc),
            **payload,
        }
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into open_finance_items
                  (id, user_id, provider, external_item_id, connector_name, institution_name, status,
                   consent_expires_at, last_sync_at, last_successful_sync_at, last_error, metadata, created_at)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (user_id, provider, external_item_id)
                do update set
                  connector_name = excluded.connector_name,
                  institution_name = excluded.institution_name,
                  status = excluded.status,
                  consent_expires_at = excluded.consent_expires_at,
                  last_sync_at = coalesce(excluded.last_sync_at, open_finance_items.last_sync_at),
                  last_successful_sync_at = coalesce(excluded.last_successful_sync_at, open_finance_items.last_successful_sync_at),
                  last_error = excluded.last_error,
                  metadata = excluded.metadata,
                  updated_at = now()
                returning *
                """,
                (
                    record["id"],
                    user_id,
                    record["provider"],
                    record["external_item_id"],
                    record.get("connector_name"),
                    record.get("institution_name"),
                    record.get("status", "active"),
                    record.get("consent_expires_at"),
                    record.get("last_sync_at"),
                    record.get("last_successful_sync_at"),
                    record.get("last_error"),
                    _adapt(record.get("metadata", {})),
                    record["created_at"],
                ),
            )
            return _record(cur.fetchone()) or {}

    def upsert_open_finance_account_link(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = {
            "id": payload.get("id") or str(uuid4()),
            "user_id": user_id,
            "provider": payload.get("provider", "pluggy"),
            "metadata": {},
            "created_at": datetime.now(timezone.utc),
            **payload,
        }
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into open_finance_account_links
                  (id, user_id, provider, external_account_id, open_finance_item_id, account_id, card_id,
                   account_type, subtype, display_name, institution_name, last_digits, metadata, created_at)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (user_id, provider, external_account_id)
                do update set
                  open_finance_item_id = excluded.open_finance_item_id,
                  account_id = excluded.account_id,
                  card_id = excluded.card_id,
                  account_type = excluded.account_type,
                  subtype = excluded.subtype,
                  display_name = excluded.display_name,
                  institution_name = excluded.institution_name,
                  last_digits = excluded.last_digits,
                  metadata = excluded.metadata,
                  updated_at = now()
                returning *
                """,
                (
                    record["id"],
                    user_id,
                    record["provider"],
                    record["external_account_id"],
                    record.get("open_finance_item_id"),
                    record.get("account_id"),
                    record.get("card_id"),
                    record.get("account_type"),
                    record.get("subtype"),
                    record.get("display_name"),
                    record.get("institution_name"),
                    record.get("last_digits"),
                    _adapt(record.get("metadata", {})),
                    record["created_at"],
                ),
            )
            return _record(cur.fetchone()) or {}

    def get_open_finance_account_link(self, user_id: str, provider: str, external_account_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            select * from open_finance_account_links
            where user_id = %s and provider = %s and external_account_id = %s
            """,
            (user_id, provider, external_account_id),
        )

    def upsert_open_finance_transaction_link(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = {
            "id": payload.get("id") or str(uuid4()),
            "user_id": user_id,
            "provider": payload.get("provider", "pluggy"),
            "metadata": {},
            "created_at": datetime.now(timezone.utc),
            **payload,
        }
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into open_finance_transaction_links
                  (id, user_id, provider, external_transaction_id, external_account_id,
                   open_finance_item_id, transaction_id, metadata, created_at)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (user_id, provider, external_transaction_id)
                do update set
                  external_account_id = excluded.external_account_id,
                  open_finance_item_id = excluded.open_finance_item_id,
                  transaction_id = excluded.transaction_id,
                  metadata = excluded.metadata,
                  updated_at = now()
                returning *
                """,
                (
                    record["id"],
                    user_id,
                    record["provider"],
                    record["external_transaction_id"],
                    record.get("external_account_id"),
                    record.get("open_finance_item_id"),
                    record["transaction_id"],
                    _adapt(record.get("metadata", {})),
                    record["created_at"],
                ),
            )
            return _record(cur.fetchone()) or {}

    def get_open_finance_transaction_link(self, user_id: str, provider: str, external_transaction_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            select * from open_finance_transaction_links
            where user_id = %s and provider = %s and external_transaction_id = %s
            """,
            (user_id, provider, external_transaction_id),
        )

    def create_open_finance_sync_run(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        return self._insert(
            "open_finance_sync_runs",
            {
                "id": payload.get("id") or str(uuid4()),
                "user_id": user_id,
                "provider": "pluggy",
                "started_at": datetime.now(timezone.utc),
                "metadata": {},
                **payload,
            },
        )

    def update_open_finance_sync_run(self, user_id: str, run_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update(
            "open_finance_sync_runs",
            payload,
            "id = %s and user_id = %s",
            (run_id, user_id),
        )

    def list_open_finance_sync_runs(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select * from open_finance_sync_runs
            where user_id = %s
            order by started_at desc
            limit %s
            """,
            (user_id, limit),
        )

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
        if not items:
            return []

        records = []
        existing_signatures = {self.transaction_signature(item) for item in self.list_transactions(user_id)}
        created_at = datetime.now(timezone.utc)
        for item in items:
            record = {
                "id": item.get("id") or str(uuid4()),
                "import_batch_id": import_id,
                "source_file_id": source_file_id,
                "user_id": user_id,
                "created_at": created_at,
                **item,
            }
            if self.transaction_signature(record) in existing_signatures:
                record["duplicate_candidate"] = True
                record["default_selected"] = False
                record["excluded_reason"] = "duplicate"
            records.append(record)

        columns = sorted({column for record in records for column in record})
        placeholders = "(" + ", ".join(["%s"] * len(columns)) + ")"
        names = ", ".join(columns)
        values_clause = ", ".join([placeholders] * len(records))
        values = tuple(_adapt(record.get(column)) for record in records for column in columns)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"insert into import_preview_items ({names}) values {values_clause} returning *",
                values,
            )
            return _records(cur.fetchall())

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

    def create_transactions(self, user_id: str, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._ensure_profile(user_id)
        if not payloads:
            return []

        created_at = datetime.now(timezone.utc)
        records = [
            {
                "id": payload.get("id") or str(uuid4()),
                "user_id": user_id,
                "normalized_description": normalize_description(payload["description"]),
                "created_at": created_at,
                **payload,
            }
            for payload in payloads
        ]
        columns = sorted({column for record in records for column in record})
        placeholders = "(" + ", ".join(["%s"] * len(columns)) + ")"
        names = ", ".join(columns)
        values_clause = ", ".join([placeholders] * len(records))
        values = tuple(_adapt(record.get(column)) for record in records for column in columns)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"insert into transactions ({names}) values {values_clause} returning *",
                values,
            )
            return _records(cur.fetchall())

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

    def mark_preview_statuses(self, user_id: str, preview_item_ids: list[str], status: PreviewStatus) -> None:
        if not preview_item_ids:
            return
        placeholders = ", ".join(["%s"] * len(preview_item_ids))
        self._execute(
            f"update import_preview_items set status = %s where user_id = %s and id in ({placeholders})",
            (status.value, user_id, *preview_item_ids),
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

    def create_stored_file(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        return self._insert(
            "stored_files",
            {
                "id": payload.get("id") or str(uuid4()),
                "owner_user_id": user_id,
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def get_stored_file(self, user_id: str, file_id: str) -> dict[str, Any] | None:
        return self._fetch_one("select * from stored_files where id = %s and owner_user_id = %s", (file_id, user_id))

    def update_stored_file(self, user_id: str, file_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update("stored_files", payload, "id = %s and owner_user_id = %s", (file_id, user_id))

    def create_transaction_attachment(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._insert(
            "transaction_attachments",
            {
                "id": payload.get("id") or str(uuid4()),
                "owner_user_id": user_id,
                "status": "active",
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def list_transaction_attachments(self, user_id: str, transaction_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select
              ta.id,
              ta.owner_user_id,
              ta.transaction_id,
              ta.file_id,
              ta.status,
              ta.created_at,
              ta.deleted_at,
              sf.storage_bucket,
              sf.storage_path,
              sf.original_filename,
              sf.declared_mime_type,
              sf.detected_mime_type,
              sf.size_bytes,
              sf.sha256_hash,
              sf.source,
              sf.status as file_status,
              sf.scan_status,
              sf.metadata,
              sf.created_at as file_created_at,
              sf.deleted_at as file_deleted_at
            from transaction_attachments ta
            join stored_files sf on sf.id = ta.file_id
            where ta.owner_user_id = %s and ta.transaction_id = %s and ta.status = 'active'
            order by ta.created_at desc
            """,
            (user_id, transaction_id),
        )

    def get_transaction_attachment(self, user_id: str, attachment_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            "select * from transaction_attachments where id = %s and owner_user_id = %s",
            (attachment_id, user_id),
        )

    def delete_transaction_attachment(self, user_id: str, attachment_id: str) -> dict[str, Any] | None:
        return self._update(
            "transaction_attachments",
            {"status": "inactive", "deleted_at": datetime.now(timezone.utc)},
            "id = %s and owner_user_id = %s",
            (attachment_id, user_id),
        )

    def create_stored_file_event(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._insert(
            "stored_file_events",
            {
                "id": payload.get("id") or str(uuid4()),
                "owner_user_id": user_id,
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def list_orphan_stored_files(self, user_id: str, older_than: datetime) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select sf.*
            from stored_files sf
            where sf.owner_user_id = %s
              and sf.created_at < %s
              and sf.status in ('uploaded', 'quarantined', 'available')
              and not exists (
                select 1
                from transaction_attachments ta
                where ta.file_id = sf.id and ta.status = 'active'
              )
            order by sf.created_at
            """,
            (user_id, older_than),
        )

    def list_reimbursement_contacts(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            "select * from reimbursement_contacts where owner_user_id = %s order by created_at desc",
            (user_id,),
        )

    def get_reimbursement_contact(self, user_id: str, contact_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            "select * from reimbursement_contacts where id = %s and owner_user_id = %s",
            (contact_id, user_id),
        )

    def create_reimbursement_contact(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        now = datetime.now(timezone.utc)
        return self._insert(
            "reimbursement_contacts",
            {
                "id": payload.get("id") or str(uuid4()),
                "owner_user_id": user_id,
                "status": "active",
                "metadata": {},
                "created_at": now,
                "updated_at": now,
                **payload,
            },
        )

    def update_reimbursement_contact(self, user_id: str, contact_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update(
            "reimbursement_contacts",
            {**payload, "updated_at": datetime.now(timezone.utc)},
            "id = %s and owner_user_id = %s",
            (contact_id, user_id),
        )

    def list_reimbursement_claims(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            "select * from reimbursement_claims where owner_user_id = %s order by created_at desc",
            (user_id,),
        )

    def get_reimbursement_claim(self, user_id: str, claim_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            "select * from reimbursement_claims where id = %s and owner_user_id = %s",
            (claim_id, user_id),
        )

    def create_reimbursement_claim(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        return self._insert(
            "reimbursement_claims",
            {
                "id": payload.get("id") or str(uuid4()),
                "owner_user_id": user_id,
                "status": "draft",
                "version": 1,
                "view_count": 0,
                "created_at": now,
                "updated_at": now,
                **payload,
            },
        )

    def update_reimbursement_claim(self, user_id: str, claim_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update(
            "reimbursement_claims",
            {**payload, "updated_at": datetime.now(timezone.utc)},
            "id = %s and owner_user_id = %s",
            (claim_id, user_id),
        )

    def list_reimbursement_items(self, user_id: str, claim_id: str | None = None) -> list[dict[str, Any]]:
        if claim_id:
            return self._fetch_all(
                "select * from reimbursement_items where owner_user_id = %s and claim_id = %s order by position, created_at",
                (user_id, claim_id),
            )
        return self._fetch_all(
            "select * from reimbursement_items where owner_user_id = %s order by created_at desc",
            (user_id,),
        )

    def list_reimbursement_items_by_transaction(self, user_id: str, transaction_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select ri.*
            from reimbursement_items ri
            join reimbursement_claims rc on rc.id = ri.claim_id
            where ri.owner_user_id = %s
              and ri.transaction_id = %s
              and ri.status = 'active'
              and rc.status <> 'canceled'
            """,
            (user_id, transaction_id),
        )

    def get_reimbursement_item(self, user_id: str, item_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            "select * from reimbursement_items where id = %s and owner_user_id = %s",
            (item_id, user_id),
        )

    def create_reimbursement_item(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._insert(
            "reimbursement_items",
            {
                "id": payload.get("id") or str(uuid4()),
                "owner_user_id": user_id,
                "status": "active",
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def create_reimbursement_item_with_allocation(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        requested = Decimal(str(payload["amount_requested"])).quantize(Decimal("0.01"))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "select * from transactions where id = %s and user_id = %s for update",
                (payload["transaction_id"], user_id),
            )
            transaction = _record(cur.fetchone())
            if not transaction:
                return {"error": "transaction_not_found"}
            if transaction.get("type") != "expense" or Decimal(str(transaction.get("amount", "0"))) == Decimal("0"):
                return {"error": "transaction_not_reimbursable"}
            cur.execute(
                """
                select 1
                from reimbursement_items
                where owner_user_id = %s
                  and claim_id = %s
                  and transaction_id = %s
                  and status = 'active'
                limit 1
                """,
                (user_id, payload["claim_id"], payload["transaction_id"]),
            )
            if cur.fetchone():
                return {"error": "reimbursement_item_duplicate"}
            cur.execute(
                """
                select coalesce(sum(ri.amount_requested), 0) as allocated_amount
                from reimbursement_items ri
                join reimbursement_claims rc on rc.id = ri.claim_id
                where ri.owner_user_id = %s
                  and ri.transaction_id = %s
                  and ri.status = 'active'
                  and rc.status <> 'canceled'
                """,
                (user_id, payload["transaction_id"]),
            )
            allocated = Decimal(str((cur.fetchone() or {}).get("allocated_amount", "0"))).quantize(Decimal("0.01"))
            if allocated + requested > abs(Decimal(str(transaction["amount"]))).quantize(Decimal("0.01")):
                return {"error": "reimbursement_amount_exceeds_transaction"}

            record = {
                "id": payload.get("id") or str(uuid4()),
                "owner_user_id": user_id,
                "status": "active",
                "created_at": datetime.now(timezone.utc),
                **payload,
            }
            data = {key: value for key, value in record.items() if value is not None}
            columns = list(data.keys())
            placeholders = ", ".join(["%s"] * len(columns))
            names = ", ".join(columns)
            values = tuple(_adapt(data[column]) for column in columns)
            cur.execute(f"insert into reimbursement_items ({names}) values ({placeholders}) returning *", values)
            return {"item": _record(cur.fetchone()) or {}}

    def update_reimbursement_item(self, user_id: str, item_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update(
            "reimbursement_items",
            payload,
            "id = %s and owner_user_id = %s",
            (item_id, user_id),
        )

    def update_reimbursement_item_with_allocation(self, user_id: str, item_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        requested = Decimal(str(payload["amount_requested"])).quantize(Decimal("0.01"))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "select * from reimbursement_items where id = %s and owner_user_id = %s for update",
                (item_id, user_id),
            )
            current = _record(cur.fetchone())
            if not current:
                return {"error": "reimbursement_item_not_found"}
            cur.execute(
                "select * from transactions where id = %s and user_id = %s for update",
                (current["transaction_id"], user_id),
            )
            transaction = _record(cur.fetchone())
            if not transaction:
                return {"error": "transaction_not_found"}
            if transaction.get("type") != "expense" or Decimal(str(transaction.get("amount", "0"))) == Decimal("0"):
                return {"error": "transaction_not_reimbursable"}
            cur.execute(
                """
                select coalesce(sum(ri.amount_requested), 0) as allocated_amount
                from reimbursement_items ri
                join reimbursement_claims rc on rc.id = ri.claim_id
                where ri.owner_user_id = %s
                  and ri.transaction_id = %s
                  and ri.status = 'active'
                  and rc.status <> 'canceled'
                  and ri.id <> %s
                """,
                (user_id, current["transaction_id"], item_id),
            )
            allocated = Decimal(str((cur.fetchone() or {}).get("allocated_amount", "0"))).quantize(Decimal("0.01"))
            if allocated + requested > abs(Decimal(str(transaction["amount"]))).quantize(Decimal("0.01")):
                return {"error": "reimbursement_amount_exceeds_transaction"}
            data = {key: value for key, value in payload.items() if value is not None}
            columns = list(data.keys())
            assignments = ", ".join(f"{column} = %s" for column in columns)
            values = tuple(_adapt(data[column]) for column in columns)
            cur.execute(
                f"update reimbursement_items set {assignments} where id = %s and owner_user_id = %s returning *",
                values + (item_id, user_id),
            )
            return {"item": _record(cur.fetchone()) or {}}

    def create_reimbursement_event(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._insert(
            "reimbursement_events",
            {
                "id": payload.get("id") or str(uuid4()),
                "owner_user_id": user_id,
                "actor_type": "owner",
                "actor_user_id": user_id,
                "metadata": {},
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def list_reimbursement_events(self, user_id: str, claim_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select * from reimbursement_events
            where owner_user_id = %s and claim_id = %s
            order by created_at
            """,
            (user_id, claim_id),
        )

    def create_reimbursement_comment(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._insert(
            "reimbursement_comments",
            {
                "id": payload.get("id") or str(uuid4()),
                "owner_user_id": user_id,
                "updated_at": None,
                "deleted_at": None,
                "deleted_by_user_id": None,
                "deleted_by_role": None,
                **payload,
            },
        )

    def list_reimbursement_comments(self, user_id: str, claim_id: str, limit: int = 50, cursor: str | None = None) -> list[dict[str, Any]]:
        params: list[Any] = [user_id, claim_id]
        cursor_filter = ""
        if cursor:
            try:
                created_at, comment_id = cursor.rsplit("|", 1)
            except ValueError:
                created_at, comment_id = "", ""
            if created_at and comment_id:
                cursor_filter = "and (created_at, id) > (%s::timestamptz, %s::uuid)"
                params.extend([created_at, comment_id])
        params.append(limit)
        return self._fetch_all(
            f"""
            select * from reimbursement_comments
            where owner_user_id = %s
              and claim_id = %s
              and deleted_at is null
              {cursor_filter}
            order by created_at, id
            limit %s
            """,
            tuple(params),
        )

    def get_reimbursement_comment(self, user_id: str, comment_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            "select * from reimbursement_comments where id = %s and owner_user_id = %s",
            (comment_id, user_id),
        )

    def update_reimbursement_comment(self, user_id: str, comment_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update(
            "reimbursement_comments",
            payload,
            "id = %s and owner_user_id = %s",
            (comment_id, user_id),
        )

    def list_reimbursement_invitations(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            "select * from reimbursement_invitations where owner_user_id = %s order by created_at desc",
            (user_id,),
        )

    def get_reimbursement_invitation(self, user_id: str, invitation_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            "select * from reimbursement_invitations where id = %s and owner_user_id = %s",
            (invitation_id, user_id),
        )

    def get_reimbursement_invitation_by_token_hash(self, token_hash: str) -> dict[str, Any] | None:
        return self._fetch_one("select * from reimbursement_invitations where token_hash = %s", (token_hash,))

    def create_reimbursement_invitation(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._insert(
            "reimbursement_invitations",
            {
                "id": payload.get("id") or str(uuid4()),
                "owner_user_id": user_id,
                **payload,
            },
        )

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
        attempt_id = str(uuid4())
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("select pg_advisory_xact_lock(hashtext(%s))", (f"{token_hash}:{ip_hash}",))
            cur.execute(
                """
                select count(*) as attempt_count
                from reimbursement_invitation_accept_attempts
                where token_hash = %s
                  and ip_hash = %s
                  and attempted_at >= %s
                """,
                (token_hash, ip_hash, window_started_at),
            )
            attempt_count = int(cur.fetchone()["attempt_count"])
            allowed = attempt_count < max_attempts
            cur.execute(
                """
                insert into reimbursement_invitation_accept_attempts
                  (id, token_hash, ip_hash, auth_user_id, attempted_at, success, failure_code)
                values (%s, %s, %s, %s, %s, false, %s)
                returning id
                """,
                (attempt_id, token_hash, ip_hash, auth_user_id, attempted_at, None if allowed else "rate_limited"),
            )
            return {"allowed": allowed, "attempt_id": str(cur.fetchone()["id"])}

    def complete_invitation_accept_attempt(self, attempt_id: str, *, success: bool, failure_code: str | None) -> None:
        self._execute(
            """
            update reimbursement_invitation_accept_attempts
            set success = %s, failure_code = %s
            where id = %s
            """,
            (success, failure_code, attempt_id),
        )

    def update_reimbursement_invitation(self, user_id: str, invitation_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update(
            "reimbursement_invitations",
            payload,
            "id = %s and owner_user_id = %s",
            (invitation_id, user_id),
        )

    def list_reimbursement_memberships(self, user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            "select * from reimbursement_memberships where owner_user_id = %s order by created_at desc",
            (user_id,),
        )

    def get_reimbursement_membership(self, user_id: str, membership_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            "select * from reimbursement_memberships where id = %s and owner_user_id = %s",
            (membership_id, user_id),
        )

    def get_active_reimbursement_membership(self, user_id: str, contact_id: str, auth_user_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            select * from reimbursement_memberships
            where owner_user_id = %s and contact_id = %s and auth_user_id = %s and status = 'active'
            limit 1
            """,
            (user_id, contact_id, auth_user_id),
        )

    def create_reimbursement_membership(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._insert(
            "reimbursement_memberships",
            {
                "id": payload.get("id") or str(uuid4()),
                "owner_user_id": user_id,
                **payload,
            },
        )

    def accept_reimbursement_invitation_atomic(self, token_hash: str, auth_user_id: str, email: str, now: datetime) -> dict[str, Any]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("select * from reimbursement_invitations where token_hash = %s for update", (token_hash,))
            invitation = _record(cur.fetchone())
            if not invitation:
                return {"error": "reimbursement_invitation_invalid"}
            normalized_email = email.strip().casefold()
            if str(invitation["email"]).strip().casefold() != normalized_email:
                return {"error": "reimbursement_invitation_invalid"}
            if invitation.get("status") == "accepted" and invitation.get("accepted_by_user_id") == auth_user_id:
                cur.execute(
                    """
                    select * from reimbursement_memberships
                    where owner_user_id = %s and contact_id = %s and auth_user_id = %s and status = 'active'
                    limit 1
                    """,
                    (invitation["owner_user_id"], invitation["contact_id"], auth_user_id),
                )
                membership = _record(cur.fetchone())
                return {"membership": membership} if membership else {"error": "reimbursement_invitation_invalid"}
            if invitation.get("status") != "pending" or invitation["expires_at"] < now:
                return {"error": "reimbursement_invitation_invalid"}
            membership_id = str(uuid4())
            cur.execute(
                """
                insert into reimbursement_memberships
                  (id, owner_user_id, contact_id, auth_user_id, email, status, linked_at, created_at)
                values (%s, %s, %s, %s, %s, 'active', %s, %s)
                on conflict (owner_user_id, contact_id, auth_user_id) where status = 'active'
                do update set email = excluded.email
                returning *
                """,
                (
                    membership_id,
                    invitation["owner_user_id"],
                    invitation["contact_id"],
                    auth_user_id,
                    normalized_email,
                    now,
                    now,
                ),
            )
            membership = _record(cur.fetchone())
            cur.execute(
                """
                update reimbursement_invitations
                set status = 'accepted', accepted_at = %s, accepted_by_user_id = %s
                where id = %s and owner_user_id = %s
                """,
                (now, auth_user_id, invitation["id"], invitation["owner_user_id"]),
            )
            return {"membership": membership, "invitation": invitation}

    def update_reimbursement_membership(self, user_id: str, membership_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update(
            "reimbursement_memberships",
            payload,
            "id = %s and owner_user_id = %s",
            (membership_id, user_id),
        )

    def list_guest_reimbursement_claims(self, guest_user_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select distinct rc.*
            from reimbursement_claims rc
            join reimbursement_memberships rm
              on rm.owner_user_id = rc.owner_user_id
             and rm.contact_id = rc.contact_id
             and rm.status = 'active'
            where rm.auth_user_id = %s
              and rc.status in ('sent', 'acknowledged', 'disputed', 'partially_paid', 'paid', 'canceled')
            order by rc.created_at desc
            """,
            (guest_user_id,),
        )

    def get_guest_reimbursement_claim(self, guest_user_id: str, claim_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            select rc.*
            from reimbursement_claims rc
            join reimbursement_memberships rm
              on rm.owner_user_id = rc.owner_user_id
             and rm.contact_id = rc.contact_id
             and rm.status = 'active'
            where rm.auth_user_id = %s
              and rc.id = %s
              and rc.status in ('sent', 'acknowledged', 'disputed', 'partially_paid', 'paid', 'canceled')
            limit 1
            """,
            (guest_user_id, claim_id),
        )

    def create_reimbursement_claim_attachment(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = {
            "id": payload.get("id") or str(uuid4()),
            "owner_user_id": user_id,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            **payload,
        }
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into reimbursement_claim_attachments
                  (id, owner_user_id, claim_id, file_id, status, created_at)
                values (%s, %s, %s, %s, %s, %s)
                on conflict (claim_id, file_id) where status = 'active'
                do update set status = excluded.status
                returning *
                """,
                (
                    record["id"],
                    record["owner_user_id"],
                    record["claim_id"],
                    record["file_id"],
                    record["status"],
                    record["created_at"],
                ),
            )
            return _record(cur.fetchone()) or {}

    def list_reimbursement_claim_attachments(self, user_id: str, claim_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            select * from reimbursement_claim_attachments
            where owner_user_id = %s and claim_id = %s and status = 'active'
            order by created_at desc
            """,
            (user_id, claim_id),
        )

    def get_reimbursement_claim_attachment(self, user_id: str, attachment_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            "select * from reimbursement_claim_attachments where id = %s and owner_user_id = %s",
            (attachment_id, user_id),
        )

    def update_reimbursement_claim_attachment(self, user_id: str, attachment_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update(
            "reimbursement_claim_attachments",
            payload,
            "id = %s and owner_user_id = %s",
            (attachment_id, user_id),
        )

    def list_reimbursement_candidate_transactions(self, user_id: str, query: str | None = None, limit: int = 30) -> list[dict[str, Any]]:
        params: list[Any] = [user_id, user_id]
        search = ""
        if query and query.strip():
            search = "and t.description ilike %s"
            params.append(f"%{query.strip()}%")
        params.append(limit)
        return self._fetch_all(
            f"""
            select
              t.*,
              coalesce(a.allocated_amount, 0) as allocated_amount
            from transactions t
            left join (
              select ri.transaction_id, sum(ri.amount_requested) as allocated_amount
              from reimbursement_items ri
              join reimbursement_claims rc on rc.id = ri.claim_id
              where ri.owner_user_id = %s
                and ri.status = 'active'
                and rc.status <> 'canceled'
              group by ri.transaction_id
            ) a on a.transaction_id = t.id
            where t.user_id = %s
              {search}
            order by t.transaction_date desc, t.created_at desc
            limit %s
            """,
            tuple(params),
        )

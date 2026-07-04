from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

import psycopg
from psycopg.types.json import Jsonb

from app.core.config import settings
from app.models.enums import (
    AccountType,
    ClassificationMatchScope,
    EntityStatus,
    PreviewStatus,
    TransactionStatus,
    TransactionType,
)
from scripts.apply_migrations import apply_migrations
from scripts.backup_local import create_backup


TABLE_ORDER = [
    "categories",
    "accounts",
    "cards",
    "import_files",
    "import_batches",
    "card_statements",
    "import_preview_items",
    "transactions",
    "classification_rules",
]

TABLE_COLUMNS = {
    "categories": {"id", "user_id", "name", "type", "status", "is_system", "created_at"},
    "accounts": {"id", "user_id", "name", "institution", "agency", "account_number", "type", "balance", "status", "created_at"},
    "cards": {"id", "user_id", "account_id", "name", "institution", "brand", "last_digits", "limit_amount", "closing_day", "due_day", "status", "created_at"},
    "import_files": {"id", "user_id", "filename", "storage_path", "mime_type", "size_bytes", "created_at"},
    "import_batches": {"id", "user_id", "source_file_id", "status", "created_at"},
    "card_statements": {"id", "user_id", "card_id", "reference_month", "due_date", "closing_date", "total_amount", "minimum_payment_amount", "status", "paid_at", "source_file_id", "created_at"},
    "import_preview_items": {
        "id", "user_id", "import_batch_id", "source_file_id", "account_id", "card_id", "card_statement_id",
        "transaction_date", "description", "original_description", "amount", "type", "category_id", "suggested_category",
        "merchant_country", "installment_current", "installment_total", "raw_text", "raw_row", "parser_confidence",
        "needs_review", "duplicate_candidate", "default_selected", "excluded_reason", "classification_rule_id",
        "classification_label", "statement_total_amount", "statement_due_date", "statement_reference_month",
        "card_last_digits", "card_name", "card_brand", "card_institution", "card_limit_amount",
        "account_institution", "account_agency", "account_number", "account_balance", "status", "created_at",
    },
    "transactions": {
        "id", "user_id", "account_id", "card_id", "card_statement_id", "transaction_date", "description",
        "original_description", "normalized_description", "amount", "type", "category_id", "source_file_id",
        "installment_current", "installment_total", "status", "created_at",
    },
    "classification_rules": {"id", "user_id", "keyword", "category_id", "transaction_type", "priority", "status", "match_scope", "auto_created", "created_at"},
}

ENUMS = {
    ("accounts", "type"): {item.value for item in AccountType},
    ("accounts", "status"): {item.value for item in EntityStatus},
    ("cards", "status"): {item.value for item in EntityStatus},
    ("categories", "type"): {"expense", "income", "both"},
    ("categories", "status"): {item.value for item in EntityStatus},
    ("card_statements", "status"): {"open", "closed", "paid", "partial", "overdue"},
    ("import_preview_items", "type"): {item.value for item in TransactionType},
    ("import_preview_items", "status"): {item.value for item in PreviewStatus},
    ("transactions", "type"): {item.value for item in TransactionType},
    ("transactions", "status"): {item.value for item in TransactionStatus},
    ("classification_rules", "transaction_type"): {item.value for item in TransactionType},
    ("classification_rules", "status"): {item.value for item in EntityStatus},
    ("classification_rules", "match_scope"): {item.value for item in ClassificationMatchScope},
}

REFERENCES = [
    ("accounts", "user_id", "profiles"),
    ("cards", "user_id", "profiles"),
    ("cards", "account_id", "accounts"),
    ("import_files", "user_id", "profiles"),
    ("import_batches", "user_id", "profiles"),
    ("import_batches", "source_file_id", "import_files"),
    ("card_statements", "user_id", "profiles"),
    ("card_statements", "card_id", "cards"),
    ("card_statements", "source_file_id", "import_files"),
    ("import_preview_items", "user_id", "profiles"),
    ("import_preview_items", "import_batch_id", "import_batches"),
    ("import_preview_items", "source_file_id", "import_files"),
    ("import_preview_items", "account_id", "accounts"),
    ("import_preview_items", "card_id", "cards"),
    ("import_preview_items", "card_statement_id", "card_statements"),
    ("import_preview_items", "category_id", "categories"),
    ("transactions", "user_id", "profiles"),
    ("transactions", "account_id", "accounts"),
    ("transactions", "card_id", "cards"),
    ("transactions", "card_statement_id", "card_statements"),
    ("transactions", "category_id", "categories"),
    ("transactions", "source_file_id", "import_files"),
    ("classification_rules", "user_id", "profiles"),
    ("classification_rules", "category_id", "categories"),
]


def load_json(path: Path) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        raise SystemExit(f"JSON database not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    for table in TABLE_ORDER:
        data.setdefault(table, [])
    return data


def user_ids(data: dict[str, list[dict[str, Any]]]) -> set[str]:
    ids: set[str] = set()
    for table in TABLE_ORDER:
        for item in data[table]:
            value = item.get("user_id")
            if value:
                ids.add(value)
    ids.add(settings.dev_user_id)
    return ids


def repair_orphan_account_refs(data: dict[str, list[dict[str, Any]]]) -> list[str]:
    repairs: list[str] = []
    accounts = data["accounts"]
    account_ids = {item["id"] for item in accounts if item.get("id")}
    now = datetime.now(timezone.utc).isoformat()

    def add_account(account_id: str, source: dict[str, Any], *, status: str) -> None:
        if account_id in account_ids:
            return
        accounts.append(
            {
                "id": account_id,
                "user_id": source.get("user_id") or settings.dev_user_id,
                "name": source.get("account_institution") or source.get("institution") or "Conta recuperada da migracao",
                "institution": source.get("account_institution") or source.get("institution"),
                "agency": source.get("account_agency"),
                "account_number": source.get("account_number"),
                "type": "checking",
                "balance": source.get("account_balance") or "0",
                "status": status,
                "created_at": now,
            }
        )
        account_ids.add(account_id)

    for card in data["cards"]:
        account_id = card.get("account_id")
        if account_id and account_id not in account_ids:
            add_account(account_id, card, status=card.get("status") or "inactive")
            repairs.append(f"Conta placeholder criada para card {card.get('id')} ({account_id}).")

    for item in data["import_preview_items"]:
        account_id = item.get("account_id")
        if account_id and account_id not in account_ids:
            add_account(account_id, item, status="active")
            repairs.append(f"Conta placeholder criada para preview {item.get('id')} ({account_id}).")

    return repairs


def table_ids(data: dict[str, list[dict[str, Any]]]) -> dict[str, set[str]]:
    ids = {table: {item["id"] for item in data[table] if item.get("id")} for table in TABLE_ORDER}
    ids["profiles"] = user_ids(data)
    return ids


def validate_uuid(value: Any, errors: list[str], label: str) -> None:
    if value is None:
        return
    try:
        UUID(str(value))
    except ValueError:
        errors.append(f"{label}: ID invalido ({value})")


def validate(data: dict[str, list[dict[str, Any]]]) -> list[str]:
    errors: list[str] = []
    ids = table_ids(data)

    for table in TABLE_ORDER:
        for index, item in enumerate(data[table], start=1):
            validate_uuid(item.get("id"), errors, f"{table}[{index}].id")
            for key, value in item.items():
                if key.endswith("_id"):
                    validate_uuid(value, errors, f"{table}[{index}].{key}")
            for (enum_table, enum_column), allowed in ENUMS.items():
                if enum_table == table and item.get(enum_column) is not None and item[enum_column] not in allowed:
                    errors.append(f"{table}[{index}].{enum_column}: enum invalido ({item[enum_column]})")

    for table, column, target_table in REFERENCES:
        for index, item in enumerate(data[table], start=1):
            value = item.get(column)
            if value and value not in ids[target_table]:
                errors.append(f"{table}[{index}].{column}: referencia ausente em {target_table} ({value})")

    seen_signatures: dict[tuple[Any, ...], str] = {}
    for item in data["transactions"]:
        signature = (
            item.get("user_id"),
            item.get("account_id") or item.get("card_id"),
            item.get("transaction_date"),
            item.get("normalized_description"),
            str(item.get("amount")),
            item.get("installment_current") or 0,
            item.get("installment_total") or 0,
        )
        if signature in seen_signatures:
            errors.append(f"transactions: assinatura duplicada entre {seen_signatures[signature]} e {item.get('id')}")
        seen_signatures[signature] = item.get("id", "")

    return errors


def clean_record(table: str, item: dict[str, Any]) -> dict[str, Any]:
    record = {key: value for key, value in item.items() if key in TABLE_COLUMNS[table]}
    if table == "card_statements" and "reported_total" in item and "total_amount" not in record:
        record["total_amount"] = item["reported_total"]
    return record


def adapt(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (dict, list)):
        return Jsonb(value)
    return value


def upsert(cur: psycopg.Cursor, table: str, item: dict[str, Any]) -> None:
    record = clean_record(table, item)
    columns = list(record.keys())
    names = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    assignments = ", ".join(f"{column} = excluded.{column}" for column in columns if column != "id")
    conflict_action = f"do update set {assignments}" if assignments else "do nothing"
    cur.execute(
        f"insert into {table} ({names}) values ({placeholders}) on conflict (id) {conflict_action}",
        tuple(adapt(record[column]) for column in columns),
    )


def apply_data(database_url: str, data: dict[str, list[dict[str, Any]]]) -> Path:
    backup_dir = create_backup()
    apply_migrations(database_url)
    with psycopg.connect(database_url) as conn:
        with conn.transaction(), conn.cursor() as cur:
            for user_id in sorted(user_ids(data)):
                cur.execute(
                    """
                    insert into profiles (id, email, full_name)
                    values (%s, %s, %s)
                    on conflict (id) do nothing
                    """,
                    (user_id, f"{user_id}@financy.local", "Migrated User"),
                )
            cur.execute("delete from categories where user_id is null and is_system = true")
            for table in TABLE_ORDER:
                for item in data[table]:
                    upsert(cur, table, item)
    return backup_dir


def database_counts(database_url: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        for table in TABLE_ORDER:
            cur.execute(f"select count(*) from {table}")
            counts[table] = cur.fetchone()[0]
    return counts


def print_report(data: dict[str, list[dict[str, Any]]], database_url: str | None = None) -> None:
    print("JSON counts:")
    for table in TABLE_ORDER:
        print(f"- {table}: {len(data[table])}")
    if database_url:
        print("PostgreSQL counts:")
        for table, count in database_counts(database_url).items():
            print(f"- {table}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate Financy local JSON data to PostgreSQL.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Validate and report without writing to PostgreSQL.")
    mode.add_argument("--apply", action="store_true", help="Create backup and write data to PostgreSQL.")
    parser.add_argument("--json-path", type=Path, default=settings.upload_dir / "local_dev_db.json")
    parser.add_argument("--database-url", default=settings.database_url)
    args = parser.parse_args()

    started_at = datetime.now().isoformat(timespec="seconds")
    data = load_json(args.json_path)
    repairs = repair_orphan_account_refs(data)
    errors = validate(data)

    print(f"Migration check started at: {started_at}")
    print_report(data)
    if repairs:
        print("Migration repairs:")
        for repair in repairs:
            print(f"- {repair}")

    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("Validation: ok")
    if args.dry_run:
        return
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required for --apply.")

    backup_dir = apply_data(args.database_url, data)
    print(f"Backup created: {backup_dir}")
    print_report(data, args.database_url)
    print("Migration apply: ok")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import os
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]


def _configured_upload_dir() -> Path:
    raw_path = os.getenv("UPLOAD_STORAGE_PATH") or os.getenv("UPLOAD_DIR") or ".uploads"
    upload_dir = Path(raw_path)
    return upload_dir if upload_dir.is_absolute() else BACKEND_DIR / upload_dir


UPLOAD_DIR = _configured_upload_dir()
DB_PATH = UPLOAD_DIR / "local_dev_db.json"
BACKUP_DIR = UPLOAD_DIR / "backups"

ENTITIES = [
    "accounts",
    "cards",
    "transactions",
    "card_statements",
    "categories",
    "classification_rules",
]

KEYWORDS = (
    "delete",
    "summary",
    "teste",
    "test",
    "orfao",
    "orphan",
    "legacy",
    "legada",
)


def _status(record: dict[str, Any]) -> str:
    return str(record.get("status") or "").lower()


def _is_active(record: dict[str, Any]) -> bool:
    return _status(record) != "inactive"


def _record_text(record: dict[str, Any]) -> str:
    return " ".join(str(value) for value in record.values() if value is not None).lower()


def _keyword_hits(record: dict[str, Any]) -> list[str]:
    text = _record_text(record)
    return [keyword for keyword in KEYWORDS if keyword in text]


def _brief(record: dict[str, Any]) -> str:
    parts = [f"id={record.get('id')}"]
    for field in (
        "name",
        "institution",
        "brand",
        "last_digits",
        "description",
        "keyword",
        "status",
    ):
        if record.get(field) not in (None, ""):
            parts.append(f"{field}={record.get(field)}")
    return ", ".join(parts)


def _counts(data: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {entity: len(data.get(entity, [])) for entity in ENTITIES}


def _status_counts(data: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, int]]:
    return {
        entity: dict(Counter(record.get("status") or "<missing>" for record in data.get(entity, [])))
        for entity in ENTITIES
    }


def _print_counts(title: str, data: dict[str, list[dict[str, Any]]]) -> None:
    print(f"\n{title}")
    counts = _counts(data)
    statuses = _status_counts(data)
    for entity in ENTITIES:
        print(f"- {entity}: {counts[entity]} {statuses[entity]}")


def _remove_inactive_test_records(
    data: dict[str, list[dict[str, Any]]],
    removals: dict[str, list[dict[str, Any]]],
) -> None:
    for entity in ("accounts", "cards", "categories", "classification_rules"):
        kept: list[dict[str, Any]] = []
        for record in data.get(entity, []):
            if not _is_active(record) and _keyword_hits(record):
                removals[entity].append(record)
                continue
            kept.append(record)
        data[entity] = kept


def _remove_test_transactions(
    data: dict[str, list[dict[str, Any]]],
    removals: dict[str, list[dict[str, Any]]],
) -> None:
    kept: list[dict[str, Any]] = []
    for record in data.get("transactions", []):
        description = str(record.get("description") or "").upper()
        if "COMPRA DELETE" in description:
            removals["transactions"].append(record)
            continue
        kept.append(record)
    data["transactions"] = kept


def _remove_orphan_statements(
    data: dict[str, list[dict[str, Any]]],
    removals: dict[str, list[dict[str, Any]]],
) -> None:
    cards = {record.get("id"): record for record in data.get("cards", [])}
    active_cards = {card_id: record for card_id, record in cards.items() if _is_active(record)}

    kept: list[dict[str, Any]] = []
    for record in data.get("card_statements", []):
        card_id = record.get("card_id")
        statement_status = _status(record)
        missing_card = not card_id or card_id not in cards
        open_or_overdue_without_active_card = (
            statement_status in {"open", "overdue"} and card_id not in active_cards
        )

        if missing_card or open_or_overdue_without_active_card:
            removals["card_statements"].append(record)
            continue
        kept.append(record)
    data["card_statements"] = kept


def _cleanup(data: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    removals: dict[str, list[dict[str, Any]]] = defaultdict(list)
    _remove_inactive_test_records(data, removals)
    _remove_test_transactions(data, removals)
    _remove_orphan_statements(data, removals)
    return removals


def _audit(data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    accounts = {record.get("id"): record for record in data.get("accounts", [])}
    active_accounts = {
        account_id: record for account_id, record in accounts.items() if _is_active(record)
    }
    cards = {record.get("id"): record for record in data.get("cards", [])}
    active_cards = {card_id: record for card_id, record in cards.items() if _is_active(record)}
    categories = {record.get("id"): record for record in data.get("categories", [])}
    active_categories = {
        category_id: record for category_id, record in categories.items() if _is_active(record)
    }

    active_suspicious_accounts = [
        record for record in data.get("accounts", []) if _is_active(record) and _keyword_hits(record)
    ]
    active_suspicious_cards = [
        record for record in data.get("cards", []) if _is_active(record) and _keyword_hits(record)
    ]

    orphan_open_statements = []
    for record in data.get("card_statements", []):
        if _status(record) not in {"open", "overdue"}:
            continue
        card_id = record.get("card_id")
        if not card_id or card_id not in active_cards:
            orphan_open_statements.append(record)

    broken_transactions = []
    for record in data.get("transactions", []):
        reasons: list[str] = []
        account_id = record.get("account_id")
        card_id = record.get("card_id")
        category_id = record.get("category_id")

        if account_id and account_id not in active_accounts:
            reasons.append("account_missing_or_inactive")
        if card_id and card_id not in active_cards:
            reasons.append("card_missing_or_inactive")
        if category_id and category_id not in active_categories:
            reasons.append("category_missing_or_inactive")
        if not account_id and not card_id:
            reasons.append("no_account_or_card")

        if reasons:
            item = dict(record)
            item["_reasons"] = reasons
            broken_transactions.append(item)

    duplicate_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in data.get("accounts", []):
        if not _is_active(record):
            continue
        key = (
            str(record.get("name") or "").strip().lower(),
            str(record.get("institution") or "").strip().lower(),
        )
        if all(key):
            duplicate_groups[key].append(record)

    duplicate_active_accounts = {
        key: records for key, records in duplicate_groups.items() if len(records) > 1
    }

    return {
        "active_suspicious_accounts": active_suspicious_accounts,
        "active_suspicious_cards": active_suspicious_cards,
        "orphan_open_statements": orphan_open_statements,
        "broken_transactions": broken_transactions,
        "duplicate_active_accounts": duplicate_active_accounts,
    }


def _print_removals(removals: dict[str, list[dict[str, Any]]]) -> None:
    print("\nRemoved records")
    for entity in ENTITIES:
        records = removals.get(entity, [])
        print(f"- {entity}: {len(records)}")
        for record in records[:12]:
            print(f"  - {_brief(record)}")
        if len(records) > 12:
            print(f"  - ... +{len(records) - 12} more")
    print("- inactivated: 0")


def _print_audit(audit: dict[str, Any]) -> None:
    print("\nRemaining issues for manual review")

    suspicious_accounts = audit["active_suspicious_accounts"]
    print(f"- active suspicious accounts: {len(suspicious_accounts)}")
    for record in suspicious_accounts[:12]:
        print(f"  - {_brief(record)}")
    if len(suspicious_accounts) > 12:
        print(f"  - ... +{len(suspicious_accounts) - 12} more")

    suspicious_cards = audit["active_suspicious_cards"]
    print(f"- active suspicious cards: {len(suspicious_cards)}")
    for record in suspicious_cards[:12]:
        print(f"  - {_brief(record)}")
    if len(suspicious_cards) > 12:
        print(f"  - ... +{len(suspicious_cards) - 12} more")

    orphan_statements = audit["orphan_open_statements"]
    print(f"- orphan open/overdue statements: {len(orphan_statements)}")
    for record in orphan_statements[:12]:
        print(
            "  - "
            f"id={record.get('id')}, card_id={record.get('card_id')}, "
            f"reference_month={record.get('reference_month')}, "
            f"due_date={record.get('due_date')}, status={record.get('status')}"
        )
    if len(orphan_statements) > 12:
        print(f"  - ... +{len(orphan_statements) - 12} more")

    broken_transactions = audit["broken_transactions"]
    print(f"- broken transaction references: {len(broken_transactions)}")
    for record in broken_transactions[:12]:
        print(f"  - {_brief(record)}, reasons={record.get('_reasons')}")
    if len(broken_transactions) > 12:
        print(f"  - ... +{len(broken_transactions) - 12} more")

    duplicate_accounts = audit["duplicate_active_accounts"]
    print(f"- duplicate active account groups: {len(duplicate_accounts)}")
    for key, records in list(duplicate_accounts.items())[:8]:
        print(f"  - name={key[0]}, institution={key[1]}, count={len(records)}")
        for record in records[:6]:
            print(f"    - {_brief(record)}")
        if len(records) > 6:
            print(f"    - ... +{len(records) - 6} more")


def _make_backup() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"local_dev_db_{timestamp}.json"
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean obvious Financy local development data.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write cleaned data back to backend/.uploads/local_dev_db.json.",
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        raise SystemExit(f"Local database not found: {DB_PATH}")

    original = json.loads(DB_PATH.read_text(encoding="utf-8"))
    data = json.loads(json.dumps(original))

    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Database: {DB_PATH}")
    _print_counts("Before counts", original)

    removals = _cleanup(data)
    _print_counts("After counts", data)
    _print_removals(removals)
    _print_audit(_audit(data))

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to write changes.")
        return

    backup_path = _make_backup()
    DB_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nBackup created: {backup_path}")
    print("Cleaned data written successfully.")


if __name__ == "__main__":
    main()

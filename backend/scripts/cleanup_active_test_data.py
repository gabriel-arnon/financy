from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
from collections import defaultdict
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

KEEP_DUPLICATE_ACCOUNT_ID = "5631fcd7-722c-4d69-8ecd-487970ee232b"
KEYWORDS = ("delete", "summary", "teste", "test", "orfao", "orphan", "legacy", "legada")


def _normal(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_active(record: dict[str, Any]) -> bool:
    return _normal(record.get("status") or "active") != "inactive"


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
        "status",
        "reference_month",
        "due_date",
    ):
        if record.get(field) not in (None, ""):
            parts.append(f"{field}={record.get(field)}")
    return ", ".join(parts)


def _indexes(data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    accounts = {record.get("id"): record for record in data.get("accounts", [])}
    cards = {record.get("id"): record for record in data.get("cards", [])}

    active_cards_by_account: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in data.get("cards", []):
        if _is_active(card):
            active_cards_by_account[card.get("account_id")].append(card)

    transactions_by_account: dict[str, list[dict[str, Any]]] = defaultdict(list)
    transactions_by_card: dict[str, list[dict[str, Any]]] = defaultdict(list)
    transactions_by_statement: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for transaction in data.get("transactions", []):
        transactions_by_account[transaction.get("account_id")].append(transaction)
        transactions_by_card[transaction.get("card_id")].append(transaction)
        transactions_by_statement[transaction.get("card_statement_id")].append(transaction)

    statements_by_card: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for statement in data.get("card_statements", []):
        statements_by_card[statement.get("card_id")].append(statement)

    return {
        "accounts": accounts,
        "cards": cards,
        "active_cards_by_account": active_cards_by_account,
        "transactions_by_account": transactions_by_account,
        "transactions_by_card": transactions_by_card,
        "transactions_by_statement": transactions_by_statement,
        "statements_by_card": statements_by_card,
    }


def _open_overdue_statements_for_account(
    account_id: str,
    indexes: dict[str, Any],
) -> list[dict[str, Any]]:
    statements: list[dict[str, Any]] = []
    for card in indexes["active_cards_by_account"].get(account_id, []):
        statements.extend(
            statement
            for statement in indexes["statements_by_card"].get(card.get("id"), [])
            if _normal(statement.get("status")) in {"open", "overdue"}
        )
    return statements


def _has_zero_links(account: dict[str, Any], indexes: dict[str, Any]) -> bool:
    account_id = account.get("id")
    return (
        len(indexes["active_cards_by_account"].get(account_id, [])) == 0
        and len(indexes["transactions_by_account"].get(account_id, [])) == 0
        and len(_open_overdue_statements_for_account(account_id, indexes)) == 0
    )


def _statement_has_transactions(statement: dict[str, Any], indexes: dict[str, Any]) -> bool:
    return len(indexes["transactions_by_statement"].get(statement.get("id"), [])) > 0


def _cleanup(data: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    actions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    indexes = _indexes(data)

    # Rule A: inactivate empty duplicate Conta Cartao / Banco do Brasil accounts.
    for account in data.get("accounts", []):
        if not _is_active(account):
            continue
        if account.get("id") == KEEP_DUPLICATE_ACCOUNT_ID:
            continue
        if (_normal(account.get("name")), _normal(account.get("institution"))) != (
            "conta cartao",
            "banco do brasil",
        ):
            continue
        if _has_zero_links(account, indexes):
            account["status"] = "inactive"
            actions["inactivated_duplicate_accounts"].append(account)

    indexes = _indexes(data)

    # Rule B/C: inactivate Conta Delete Fatura accounts and linked Ourocard Delete cards.
    for account in data.get("accounts", []):
        if not _is_active(account):
            continue
        if "conta delete fatura" not in _normal(account.get("name")):
            continue

        linked_active_cards = indexes["active_cards_by_account"].get(account.get("id"), [])
        if not linked_active_cards:
            continue
        if not all("ourocard delete" in _normal(card.get("name")) for card in linked_active_cards):
            continue
        if indexes["transactions_by_account"].get(account.get("id")):
            actions["skipped_delete_accounts_with_transactions"].append(account)
            continue
        linked_card_transactions = [
            transaction
            for card in linked_active_cards
            for transaction in indexes["transactions_by_card"].get(card.get("id"), [])
        ]
        if linked_card_transactions:
            actions["skipped_delete_cards_with_transactions"].extend(linked_active_cards)
            continue

        account["status"] = "inactive"
        actions["inactivated_delete_accounts"].append(account)

        for card in linked_active_cards:
            if _is_active(card):
                card["status"] = "inactive"
                actions["inactivated_delete_cards"].append(card)

            for statement in indexes["statements_by_card"].get(card.get("id"), []):
                if _normal(statement.get("status")) not in {"open", "overdue"}:
                    continue
                if _statement_has_transactions(statement, indexes):
                    actions["kept_statements_with_transactions"].append(statement)
                    continue
                actions["removed_delete_statements"].append(statement)

    removed_statement_ids = {record.get("id") for record in actions["removed_delete_statements"]}
    if removed_statement_ids:
        data["card_statements"] = [
            statement
            for statement in data.get("card_statements", [])
            if statement.get("id") not in removed_statement_ids
        ]

    return actions


def _audit(data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    indexes = _indexes(data)
    active_accounts = {
        account_id: account
        for account_id, account in indexes["accounts"].items()
        if _is_active(account)
    }
    active_cards = {card_id: card for card_id, card in indexes["cards"].items() if _is_active(card)}

    active_suspicious_accounts = [
        account for account in active_accounts.values() if _keyword_hits(account)
    ]
    active_suspicious_cards = [card for card in active_cards.values() if _keyword_hits(card)]

    orphan_open_overdue_statements = []
    for statement in data.get("card_statements", []):
        if _normal(statement.get("status")) not in {"open", "overdue"}:
            continue
        if statement.get("card_id") not in active_cards:
            orphan_open_overdue_statements.append(statement)

    active_categories = {
        category.get("id")
        for category in data.get("categories", [])
        if _is_active(category)
    }
    broken_transactions = []
    for transaction in data.get("transactions", []):
        reasons: list[str] = []
        if transaction.get("account_id") and transaction.get("account_id") not in active_accounts:
            reasons.append("account_missing_or_inactive")
        if transaction.get("card_id") and transaction.get("card_id") not in active_cards:
            reasons.append("card_missing_or_inactive")
        if transaction.get("category_id") and transaction.get("category_id") not in active_categories:
            reasons.append("category_missing_or_inactive")
        if not transaction.get("account_id") and not transaction.get("card_id"):
            reasons.append("no_account_or_card")
        if reasons:
            broken_transactions.append({"transaction": transaction, "reasons": reasons})

    duplicate_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for account in active_accounts.values():
        key = (_normal(account.get("name")), _normal(account.get("institution")))
        if all(key):
            duplicate_groups[key].append(account)

    duplicate_active_accounts = {
        key: accounts for key, accounts in duplicate_groups.items() if len(accounts) > 1
    }

    return {
        "active_suspicious_accounts": active_suspicious_accounts,
        "active_suspicious_cards": active_suspicious_cards,
        "duplicate_active_accounts": duplicate_active_accounts,
        "orphan_open_overdue_statements": orphan_open_overdue_statements,
        "broken_transactions": broken_transactions,
    }


def _counts(data: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {
        "accounts": len(data.get("accounts", [])),
        "cards": len(data.get("cards", [])),
        "transactions": len(data.get("transactions", [])),
        "card_statements": len(data.get("card_statements", [])),
        "categories": len(data.get("categories", [])),
        "classification_rules": len(data.get("classification_rules", [])),
    }


def _active_counts(data: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {
        "accounts": sum(1 for record in data.get("accounts", []) if _is_active(record)),
        "cards": sum(1 for record in data.get("cards", []) if _is_active(record)),
        "transactions": len(data.get("transactions", [])),
        "card_statements_open_overdue": sum(
            1
            for record in data.get("card_statements", [])
            if _normal(record.get("status")) in {"open", "overdue"}
        ),
    }


def _print_actions(actions: dict[str, list[dict[str, Any]]]) -> None:
    print("\nPlanned/applied changes")
    labels = (
        "inactivated_duplicate_accounts",
        "inactivated_delete_accounts",
        "inactivated_delete_cards",
        "removed_delete_statements",
        "kept_statements_with_transactions",
        "skipped_delete_accounts_with_transactions",
        "skipped_delete_cards_with_transactions",
    )
    for label in labels:
        records = actions.get(label, [])
        print(f"- {label}: {len(records)}")
        for record in records[:12]:
            print(f"  - {_brief(record)}")
        if len(records) > 12:
            print(f"  - ... +{len(records) - 12} more")


def _print_audit(audit: dict[str, Any]) -> None:
    print("\nPost-cleanup audit")
    print(f"- active suspicious accounts: {len(audit['active_suspicious_accounts'])}")
    for record in audit["active_suspicious_accounts"][:12]:
        print(f"  - {_brief(record)}")
    if len(audit["active_suspicious_accounts"]) > 12:
        print(f"  - ... +{len(audit['active_suspicious_accounts']) - 12} more")

    print(f"- active suspicious cards: {len(audit['active_suspicious_cards'])}")
    for record in audit["active_suspicious_cards"][:12]:
        print(f"  - {_brief(record)}")
    if len(audit["active_suspicious_cards"]) > 12:
        print(f"  - ... +{len(audit['active_suspicious_cards']) - 12} more")

    print(f"- duplicate active account groups: {len(audit['duplicate_active_accounts'])}")
    for key, records in audit["duplicate_active_accounts"].items():
        print(f"  - name={key[0]}, institution={key[1]}, count={len(records)}")

    print(f"- open/overdue orphan statements: {len(audit['orphan_open_overdue_statements'])}")
    for record in audit["orphan_open_overdue_statements"][:12]:
        print(f"  - {_brief(record)}")

    print(f"- broken transaction references: {len(audit['broken_transactions'])}")
    for item in audit["broken_transactions"][:12]:
        print(f"  - {_brief(item['transaction'])}, reasons={item['reasons']}")


def _make_backup() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"local_dev_db_{timestamp}_before_active_cleanup.json"
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean lowest-risk active Financy test data.")
    parser.add_argument("--apply", action="store_true", help="Write cleaned data back.")
    args = parser.parse_args()

    if not DB_PATH.exists():
        raise SystemExit(f"Local database not found: {DB_PATH}")

    original = json.loads(DB_PATH.read_text(encoding="utf-8"))
    data = copy.deepcopy(original)

    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Database: {DB_PATH}")
    print(f"Before counts: {_counts(original)}")
    print(f"Before active counts: {_active_counts(original)}")

    actions = _cleanup(data)

    print(f"After counts: {_counts(data)}")
    print(f"After active counts: {_active_counts(data)}")
    _print_actions(actions)
    _print_audit(_audit(data))

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to write changes.")
        return

    backup_path = _make_backup()
    DB_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nBackup created: {backup_path}")
    print("Cleaned data written successfully.")


if __name__ == "__main__":
    main()

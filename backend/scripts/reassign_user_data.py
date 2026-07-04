from __future__ import annotations

import argparse
import sys
from pathlib import Path
from uuid import UUID


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import psycopg

from app.core.config import settings


USER_OWNED_TABLES = [
    "accounts",
    "cards",
    "card_statements",
    "transactions",
    "classification_rules",
    "import_files",
    "import_batches",
    "import_preview_items",
    "categories",
]


def validate_uuid(value: str, label: str) -> None:
    try:
        UUID(value)
    except ValueError:
        raise SystemExit(f"{label} must be a valid UUID: {value}")


def counts(conn: psycopg.Connection, user_id: str) -> dict[str, int]:
    result: dict[str, int] = {}
    with conn.cursor() as cur:
        for table in USER_OWNED_TABLES:
            cur.execute(f"select count(*) from {table} where user_id = %s", (user_id,))
            result[table] = cur.fetchone()[0]
    return result


def print_counts(title: str, values: dict[str, int]) -> None:
    print(title)
    for table, count in values.items():
        print(f"- {table}: {count}")


def reassign(database_url: str, source_user_id: str, target_user_id: str, *, apply: bool, target_email: str | None) -> None:
    with psycopg.connect(database_url) as conn:
        before_source = counts(conn, source_user_id)
        before_target = counts(conn, target_user_id)
        print_counts("Source user counts:", before_source)
        print_counts("Target user counts:", before_target)

        if not apply:
            print("Dry-run only. No data changed.")
            return

        with conn.transaction(), conn.cursor() as cur:
            cur.execute(
                """
                insert into profiles (id, email, full_name)
                values (%s, %s, %s)
                on conflict (id) do update set email = coalesce(excluded.email, profiles.email)
                """,
                (target_user_id, target_email, "Migrated User"),
            )
            for table in USER_OWNED_TABLES:
                cur.execute(f"update {table} set user_id = %s where user_id = %s", (target_user_id, source_user_id))

        after_source = counts(conn, source_user_id)
        after_target = counts(conn, target_user_id)
        print_counts("Source user counts after apply:", after_source)
        print_counts("Target user counts after apply:", after_target)
        print("Ownership reassignment applied.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reassign Financy user-owned data from one user_id to another.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--database-url", default=settings.database_url)
    parser.add_argument("--source-user-id", default=settings.dev_user_id)
    parser.add_argument("--target-user-id", required=True)
    parser.add_argument("--target-email", default=None)
    parser.add_argument(
        "--backup-confirmation",
        default=None,
        help="Required for --apply. Pass the backup path or ticket used before reassignment.",
    )
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("DATABASE_URL is required.")
    validate_uuid(args.source_user_id, "source-user-id")
    validate_uuid(args.target_user_id, "target-user-id")
    if args.apply and not args.backup_confirmation:
        raise SystemExit("--backup-confirmation is required for --apply.")

    if args.backup_confirmation:
        print(f"Backup confirmation: {args.backup_confirmation}")

    reassign(
        args.database_url,
        args.source_user_id,
        args.target_user_id,
        apply=args.apply,
        target_email=args.target_email,
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import psycopg

from app.core.config import settings
from scripts.dev_db_safety import assert_local_database_url


EXPECTED_TABLES = {
    "profiles",
    "accounts",
    "cards",
    "categories",
    "transactions",
    "stored_files",
    "transaction_attachments",
    "stored_file_events",
    "reimbursement_contacts",
    "reimbursement_claims",
    "reimbursement_items",
    "reimbursement_events",
}


def inspect_schema(database_url: str) -> None:
    safe = assert_local_database_url(database_url, purpose="schema inspection")
    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        cur.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = 'public' and table_type = 'BASE TABLE'
            order by table_name
            """
        )
        tables = {row[0] for row in cur.fetchall()}
        missing = sorted(EXPECTED_TABLES - tables)
        if missing:
            raise RuntimeError(f"Schema is missing expected tables: {', '.join(missing)}")
        cur.execute(
            """
            select tablename, indexname
            from pg_indexes
            where schemaname = 'public'
              and tablename in ('stored_files', 'transaction_attachments', 'reimbursement_contacts', 'reimbursement_claims', 'reimbursement_items', 'reimbursement_events')
            order by tablename, indexname
            """
        )
        indexes = cur.fetchall()
        cur.execute("select count(*) from transactions")
        transaction_count = cur.fetchone()[0]
    print(f"Schema inspected on {safe.display}")
    print(f"Tables: {len(tables)} public tables")
    print(f"Foundation indexes: {len(indexes)} indexes")
    print(f"Transactions preserved in target: {transaction_count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Financy local development schema.")
    parser.add_argument("--database-url", default=settings.database_url, help="Local PostgreSQL connection string.")
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required.")
    inspect_schema(args.database_url)


if __name__ == "__main__":
    main()

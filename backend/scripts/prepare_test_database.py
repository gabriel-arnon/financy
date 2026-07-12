from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from app.core.config import settings
from scripts.dev_db_safety import assert_local_database_url
from scripts.apply_migrations import apply_migrations


def maintenance_url(database_url: str) -> tuple[str, str]:
    info = conninfo_to_dict(database_url)
    dbname = info.get("dbname")
    if not dbname:
        raise RuntimeError("Database URL must include a database name.")
    info["dbname"] = "postgres"
    return make_conninfo(**info), dbname


def ensure_database(database_url: str) -> None:
    admin_url, dbname = maintenance_url(database_url)
    with psycopg.connect(admin_url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("select 1 from pg_database where datname = %s", (dbname,))
        if cur.fetchone():
            return
        cur.execute(sql.SQL("create database {}").format(sql.Identifier(dbname)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create/reset the Financy PostgreSQL test database.")
    parser.add_argument("--database-url", default=settings.test_database_url or settings.database_url)
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("TEST_DATABASE_URL or DATABASE_URL is required.")

    safe = assert_local_database_url(args.database_url, purpose="test database preparation")
    print(f"Target test database: {safe.display}")
    ensure_database(args.database_url)
    applied = apply_migrations(args.database_url, reset=True)
    print("Test database prepared.")
    if applied:
        for name in applied:
            print(f"- {name}")
    else:
        print("- none")


if __name__ == "__main__":
    main()

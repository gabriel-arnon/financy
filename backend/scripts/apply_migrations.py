from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

import psycopg

from app.core.config import settings
from scripts.dev_db_safety import assert_local_database_url, parse_safe_database_url


MIGRATIONS_DIR = ROOT_DIR / "docs" / "supabase" / "migrations"


def reset_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("drop schema if exists public cascade")
        cur.execute("create schema public")


def ensure_migrations_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            create table if not exists schema_migrations (
              version text primary key,
              applied_at timestamptz not null default now()
            )
            """
        )


def applied_versions(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("select version from schema_migrations")
        return {row[0] for row in cur.fetchall()}


def apply_migrations(database_url: str, *, reset: bool = False) -> list[str]:
    applied: list[str] = []
    migration_paths = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_paths:
        raise RuntimeError(f"No migration files found in {MIGRATIONS_DIR}")

    with psycopg.connect(database_url) as conn:
        if reset:
            reset_schema(conn)
        ensure_migrations_table(conn)
        done = applied_versions(conn)
        for path in migration_paths:
            if path.name in done:
                continue
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(path.read_text(encoding="utf-8"))
                    cur.execute("insert into schema_migrations (version) values (%s)", (path.name,))
            applied.append(path.name)
    return applied


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Financy PostgreSQL migrations.")
    parser.add_argument("--database-url", default=settings.database_url, help="PostgreSQL connection string.")
    parser.add_argument("--reset-schema", action="store_true", help="Drop and recreate the public schema before applying.")
    parser.add_argument("--allow-remote", action="store_true", help="Explicitly allow applying migrations to a non-local database.")
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("DATABASE_URL is required.")

    allow_remote = args.allow_remote or os.getenv("FINANCY_ALLOW_REMOTE_MIGRATIONS", "").strip().lower() in {"1", "true", "yes"}
    try:
        safe = assert_local_database_url(args.database_url, purpose="migrations")
    except RuntimeError as exc:
        safe = parse_safe_database_url(args.database_url)
        print(f"Target database: {safe.display}")
        if args.reset_schema:
            raise SystemExit(f"{exc} Refusing --reset-schema on a non-local database.")
        if not allow_remote:
            print("Remote database detected; skipping migrations by default.")
            print("To run remote migrations intentionally, pass --allow-remote or set FINANCY_ALLOW_REMOTE_MIGRATIONS=true.")
            return
        print("Remote migrations explicitly enabled.")
    print(f"Target database: {safe.display}")
    applied = apply_migrations(args.database_url, reset=args.reset_schema)
    print("Migrations applied:")
    if applied:
        for name in applied:
            print(f"- {name}")
    else:
        print("- none")


if __name__ == "__main__":
    main()

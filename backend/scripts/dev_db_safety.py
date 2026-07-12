from __future__ import annotations

from dataclasses import dataclass

from psycopg.conninfo import conninfo_to_dict


LOCAL_DATABASE_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}
BLOCKED_DATABASE_HINTS = {"prod", "production"}


@dataclass(frozen=True)
class SafeDatabaseInfo:
    host: str
    port: str
    dbname: str
    user: str

    @property
    def display(self) -> str:
        return f"postgresql://{self.user}:***@{self.host}:{self.port}/{self.dbname}"


def parse_safe_database_url(database_url: str) -> SafeDatabaseInfo:
    if not database_url:
        raise RuntimeError("DATABASE_URL is required.")
    info = conninfo_to_dict(database_url)
    host = info.get("host") or "localhost"
    port = info.get("port") or "5432"
    dbname = info.get("dbname") or ""
    user = info.get("user") or ""
    if not dbname:
        raise RuntimeError("DATABASE_URL must include a database name.")
    return SafeDatabaseInfo(host=host, port=port, dbname=dbname, user=user)


def assert_local_database_url(database_url: str, *, purpose: str) -> SafeDatabaseInfo:
    safe = parse_safe_database_url(database_url)
    host = safe.host.lower()
    dbname = safe.dbname.lower()
    if host not in LOCAL_DATABASE_HOSTS:
        raise RuntimeError(
            f"Refusing to run {purpose} against non-local database host '{safe.host}'. "
            f"Allowed hosts: {', '.join(sorted(LOCAL_DATABASE_HOSTS))}."
        )
    if any(hint in dbname for hint in BLOCKED_DATABASE_HINTS):
        raise RuntimeError(f"Refusing to run {purpose} against database name '{safe.dbname}'.")
    return safe

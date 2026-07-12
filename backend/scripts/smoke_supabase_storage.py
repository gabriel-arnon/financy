from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path
from uuid import uuid4


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from starlette.datastructures import Headers, UploadFile

from app.core.config import settings
from app.repositories.postgres import PostgresRepository
from app.services.file_storage_service import FileService
from scripts.dev_db_safety import assert_local_database_url


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _storage_request(path: str, *, method: str = "GET", body: bytes | None = None) -> dict:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")
    request = urllib.request.Request(
        f"{settings.supabase_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload) if payload else {}


def _bucket_is_private() -> bool:
    bucket = urllib.parse.quote(settings.private_files_bucket)
    try:
        payload = _storage_request(f"/storage/v1/bucket/{bucket}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError("Supabase bucket not found or not accessible with backend service role.") from exc
    return payload.get("public") is False


async def run_smoke(database_url: str) -> None:
    if settings.environment.lower() == "production":
        raise RuntimeError("Refusing to run Supabase Storage smoke test with ENVIRONMENT=production.")
    if settings.private_files_backend.strip().lower() != "supabase":
        raise RuntimeError("PRIVATE_FILES_BACKEND must be 'supabase' for this smoke test.")
    if settings.private_files_scan_provider.strip().lower() == "mock" and settings.environment.lower() not in {"local", "development", "test"}:
        raise RuntimeError("FILE scan mock is only allowed in local/development/test environments.")
    safe = assert_local_database_url(database_url, purpose="Supabase Storage smoke metadata")
    if not _bucket_is_private():
        raise RuntimeError("Refusing to run smoke test against a public Supabase Storage bucket.")

    repo = PostgresRepository(database_url, dev_user_id=settings.dev_user_id)
    service = FileService(repo, settings)
    stored_file = None
    storage_path = None
    try:
        upload = UploadFile(
            filename=f"storage-smoke-{uuid4()}.png",
            file=BytesIO(PNG_BYTES),
            headers=Headers({"content-type": "image/png"}),
        )
        stored_file = await service.upload(user_id=settings.dev_user_id, file=upload, source="storage_smoke")
        record = repo.get_stored_file(settings.dev_user_id, stored_file.id)
        if not record:
            raise RuntimeError("Stored file metadata was not persisted.")
        storage_path = record["storage_path"]
        signed = service.signed_url(user_id=settings.dev_user_id, file_id=stored_file.id)
        if not signed.url:
            raise RuntimeError("Signed URL was not generated.")
        service.delete(user_id=settings.dev_user_id, file_id=stored_file.id)
        try:
            service.signed_url(user_id=settings.dev_user_id, file_id=stored_file.id)
        except Exception:
            pass
        else:
            raise RuntimeError("Deleted file still generated a signed URL.")
    finally:
        if storage_path:
            try:
                service.storage.delete(path=storage_path)
            except Exception:
                pass
        if stored_file:
            with repo._connect() as conn, conn.cursor() as cur:
                cur.execute("delete from stored_file_events where file_id = %s", (stored_file.id,))
                cur.execute("delete from stored_files where id = %s", (stored_file.id,))
        repo.pool.close()
    print(f"Supabase Storage smoke passed with metadata database {safe.display}")
    print("Signed URL was generated and validated without printing the URL.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Supabase Storage smoke test against a development bucket.")
    parser.add_argument("--database-url", default=settings.database_url, help="Local PostgreSQL database used for stored_files metadata.")
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required.")
    try:
        asyncio.run(run_smoke(args.database_url))
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()

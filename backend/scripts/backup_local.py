from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings


def _copy_upload_files(upload_dir: Path, destination: Path) -> int:
    copied = 0
    uploads_destination = destination / "uploads"
    uploads_destination.mkdir(parents=True, exist_ok=True)

    for item in upload_dir.iterdir():
        if item.name == "backups" or item.name == "local_dev_db.json":
            continue
        target = uploads_destination / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
        copied += 1

    return copied


def create_backup(output_dir: Path | None = None) -> Path:
    upload_dir = settings.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)

    backup_root = output_dir or upload_dir / "backups"
    backup_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_dir = backup_root / f"financy_local_backup_{timestamp}"
    backup_dir.mkdir()

    db_path = upload_dir / "local_dev_db.json"
    db_copied = False
    if db_path.exists():
        shutil.copy2(db_path, backup_dir / "local_dev_db.json")
        db_copied = True

    uploads_copied = _copy_upload_files(upload_dir, backup_dir)
    manifest = {
        "created_at": timestamp,
        "upload_dir": str(upload_dir),
        "database_file": str(db_path),
        "database_copied": db_copied,
        "upload_items_copied": uploads_copied,
        "restore_note": "Para restaurar manualmente, pare o backend, copie local_dev_db.json para UPLOAD_STORAGE_PATH e recoloque os arquivos de uploads conforme necessario.",
    }
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return backup_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a local Financy backup.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional destination directory. Defaults to UPLOAD_STORAGE_PATH/backups.",
    )
    args = parser.parse_args()

    backup_dir = create_backup(args.output_dir)
    print(f"Backup created: {backup_dir}")


if __name__ == "__main__":
    main()

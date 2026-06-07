from app.core.config import settings
from app.repositories.local_json import LocalJsonRepository
from app.services.import_service import ImportService
from app.services.transaction_service import TransactionService


repository = LocalJsonRepository(settings.upload_dir)


def get_user_id() -> str:
    # Future swap point: validate Supabase Auth JWT and return auth.uid().
    return settings.dev_user_id


def get_import_service() -> ImportService:
    return ImportService(repository=repository, upload_dir=settings.upload_dir)


def get_transaction_service() -> TransactionService:
    return TransactionService(repository=repository)

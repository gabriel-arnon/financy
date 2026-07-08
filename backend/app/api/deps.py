from fastapi import Request

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.repositories.factory import create_repository
from app.services.ai_import_service import AiImportAnalyzer
from app.services.import_service import ImportService
from app.services.transaction_service import TransactionService


repository = create_repository(settings)


def _ensure_profile(user: CurrentUser) -> None:
    ensure_profile = getattr(repository, "ensure_profile", None)
    if ensure_profile:
        ensure_profile(user.id, email=user.email, full_name=user.full_name)


def get_user_id() -> str:
    user = get_current_user(None)
    _ensure_profile(user)
    return user.id


def get_request_user_id(request: Request) -> str:
    user = get_current_user(request)
    _ensure_profile(user)
    return user.id


def get_import_service() -> ImportService:
    analyzer = AiImportAnalyzer(settings)
    return ImportService(repository=repository, upload_dir=settings.upload_dir, ai_analyzer=analyzer)


def get_transaction_service() -> TransactionService:
    return TransactionService(repository=repository)

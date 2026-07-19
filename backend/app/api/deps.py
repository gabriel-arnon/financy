from fastapi import Request

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.repositories.factory import create_repository
from app.services.ai_import_service import AiImportAnalyzer
from app.services.ai_finance_service import AiFinanceService
from app.services.ai_planning_service import AiPlanningAnalyzer
from app.services.ai_provider import AiProviderClient
from app.services.file_storage_service import FileService
from app.services.import_service import ImportService
from app.services.open_finance_service import OpenFinanceService
from app.services.planning_service import PlanningService
from app.services.pluggy_client import PluggyClient
from app.services.reimbursement_service import ReimbursementService
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


def get_request_user(request: Request) -> CurrentUser:
    user = get_current_user(request)
    _ensure_profile(user)
    return user


def get_import_service() -> ImportService:
    analyzer = AiImportAnalyzer(settings, provider=AiProviderClient(settings))
    return ImportService(repository=repository, upload_dir=settings.upload_dir, ai_analyzer=analyzer)


def get_transaction_service() -> TransactionService:
    return TransactionService(repository=repository)


def get_ai_finance_service() -> AiFinanceService:
    return AiFinanceService(repository=repository)


def get_file_service() -> FileService:
    return FileService(repository=repository, settings=settings)


def get_reimbursement_service() -> ReimbursementService:
    return ReimbursementService(repository=repository)


def get_open_finance_service() -> OpenFinanceService:
    return OpenFinanceService(repository=repository, settings=settings, pluggy_client=PluggyClient(settings))


def get_planning_service() -> PlanningService:
    provider = AiProviderClient(settings)
    return PlanningService(repository=repository, ai_planning_analyzer=AiPlanningAnalyzer(provider))

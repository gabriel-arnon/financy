from fastapi import APIRouter, Depends

from app.api.deps import get_ai_finance_service, get_request_user_id
from app.schemas.ai_finance import AiFinanceOverview, AiFinanceQuestionRequest, AiFinanceQuestionResponse
from app.services.ai_finance_service import AiFinanceService


router = APIRouter(prefix="/ai-finance", tags=["ai-finance"])


@router.get("/overview", response_model=AiFinanceOverview)
def get_ai_finance_overview(
    user_id: str = Depends(get_request_user_id),
    service: AiFinanceService = Depends(get_ai_finance_service),
) -> AiFinanceOverview:
    return service.overview(user_id=user_id)


@router.post("/ask", response_model=AiFinanceQuestionResponse)
def ask_ai_finance(
    payload: AiFinanceQuestionRequest,
    user_id: str = Depends(get_request_user_id),
    service: AiFinanceService = Depends(get_ai_finance_service),
) -> AiFinanceQuestionResponse:
    return service.answer(user_id=user_id, question=payload.question)

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_planning_service, get_request_user_id
from app.schemas.planning import (
    BudgetCreate,
    BudgetRead,
    BudgetUpdate,
    FinancialGoalCreate,
    FinancialGoalRead,
    FinancialGoalUpdate,
    PlanningOverview,
    RecurringItemCreate,
    RecurringItemRead,
    RecurringItemUpdate,
)
from app.services.planning_service import PlanningService


router = APIRouter(prefix="/planning", tags=["planning"])


@router.get("/overview", response_model=PlanningOverview)
def overview(
    period_month: str | None = Query(default=None),
    user_id: str = Depends(get_request_user_id),
    service: PlanningService = Depends(get_planning_service),
) -> PlanningOverview:
    return service.overview(user_id, period_month=period_month)


@router.get("/recurring-items", response_model=list[RecurringItemRead])
def list_recurring_items(
    user_id: str = Depends(get_request_user_id),
    service: PlanningService = Depends(get_planning_service),
) -> list[RecurringItemRead]:
    return service.list_recurring_items(user_id)


@router.post("/recurring-items", response_model=RecurringItemRead)
def create_recurring_item(
    payload: RecurringItemCreate,
    user_id: str = Depends(get_request_user_id),
    service: PlanningService = Depends(get_planning_service),
) -> RecurringItemRead:
    return service.create_recurring_item(user_id, payload)


@router.put("/recurring-items/{recurring_item_id}", response_model=RecurringItemRead)
def update_recurring_item(
    recurring_item_id: str,
    payload: RecurringItemUpdate,
    user_id: str = Depends(get_request_user_id),
    service: PlanningService = Depends(get_planning_service),
) -> RecurringItemRead:
    return service.update_recurring_item(user_id, recurring_item_id, payload)


@router.delete("/recurring-items/{recurring_item_id}", response_model=RecurringItemRead)
def delete_recurring_item(
    recurring_item_id: str,
    user_id: str = Depends(get_request_user_id),
    service: PlanningService = Depends(get_planning_service),
) -> RecurringItemRead:
    return service.delete_recurring_item(user_id, recurring_item_id)


@router.get("/goals", response_model=list[FinancialGoalRead])
def list_goals(
    user_id: str = Depends(get_request_user_id),
    service: PlanningService = Depends(get_planning_service),
) -> list[FinancialGoalRead]:
    return service.list_goals(user_id)


@router.post("/goals", response_model=FinancialGoalRead)
def create_goal(
    payload: FinancialGoalCreate,
    user_id: str = Depends(get_request_user_id),
    service: PlanningService = Depends(get_planning_service),
) -> FinancialGoalRead:
    return service.create_goal(user_id, payload)


@router.put("/goals/{goal_id}", response_model=FinancialGoalRead)
def update_goal(
    goal_id: str,
    payload: FinancialGoalUpdate,
    user_id: str = Depends(get_request_user_id),
    service: PlanningService = Depends(get_planning_service),
) -> FinancialGoalRead:
    return service.update_goal(user_id, goal_id, payload)


@router.delete("/goals/{goal_id}", response_model=FinancialGoalRead)
def delete_goal(
    goal_id: str,
    user_id: str = Depends(get_request_user_id),
    service: PlanningService = Depends(get_planning_service),
) -> FinancialGoalRead:
    return service.delete_goal(user_id, goal_id)


@router.get("/budgets", response_model=list[BudgetRead])
def list_budgets(
    period_month: str | None = Query(default=None),
    user_id: str = Depends(get_request_user_id),
    service: PlanningService = Depends(get_planning_service),
) -> list[BudgetRead]:
    return service.list_budgets(user_id, period_month=period_month)


@router.post("/budgets", response_model=BudgetRead)
def create_budget(
    payload: BudgetCreate,
    user_id: str = Depends(get_request_user_id),
    service: PlanningService = Depends(get_planning_service),
) -> BudgetRead:
    return service.create_budget(user_id, payload)


@router.put("/budgets/{budget_id}", response_model=BudgetRead)
def update_budget(
    budget_id: str,
    payload: BudgetUpdate,
    user_id: str = Depends(get_request_user_id),
    service: PlanningService = Depends(get_planning_service),
) -> BudgetRead:
    return service.update_budget(user_id, budget_id, payload)


@router.delete("/budgets/{budget_id}", response_model=BudgetRead)
def delete_budget(
    budget_id: str,
    user_id: str = Depends(get_request_user_id),
    service: PlanningService = Depends(get_planning_service),
) -> BudgetRead:
    return service.delete_budget(user_id, budget_id)

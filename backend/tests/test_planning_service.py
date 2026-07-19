from pathlib import Path

from app.repositories.local_json import LocalJsonRepository
from app.services.planning_service import PlanningService
from app.schemas.planning import BudgetCreate, FinancialGoalCreate, RecurringItemCreate


USER_ID = "00000000-0000-4000-8000-000000000101"


def test_planning_creates_recurring_goal_and_budget(tmp_path: Path) -> None:
    repository = LocalJsonRepository(tmp_path)
    service = PlanningService(repository)

    category = repository.categories(USER_ID)[0]
    recurring = service.create_recurring_item(
        USER_ID,
        RecurringItemCreate(
            name="Netflix",
            kind="subscription",
            amount="39.90",
            cadence="monthly",
            category_id=category["id"],
            status="active",
            source="manual",
        ),
    )
    goal = service.create_goal(
        USER_ID,
        FinancialGoalCreate(name="Reserva", target_amount="1000", current_amount="250", status="active"),
    )
    budget = service.create_budget(
        USER_ID,
        BudgetCreate(name="Assinaturas", amount="100", period_month="2026-07", category_id=category["id"], status="active"),
    )

    assert recurring.name == "Netflix"
    assert goal.progress_percent == 25
    assert goal.remaining_amount == 750
    assert budget.spent_amount == 0
    assert budget.alert_level == "ok"


def test_budget_uses_confirmed_expenses_including_open_finance(tmp_path: Path) -> None:
    repository = LocalJsonRepository(tmp_path)
    service = PlanningService(repository)
    category = repository.categories(USER_ID)[0]
    repository.create_transaction(
        USER_ID,
        {
            "account_id": None,
            "card_id": None,
            "card_statement_id": None,
            "transaction_date": "2026-07-10",
            "description": "OPENAI",
            "original_description": "OPENAI",
            "amount": "80.00",
            "type": "expense",
            "category_id": category["id"],
            "source_file_id": None,
            "installment_current": None,
            "installment_total": None,
            "status": "confirmed",
            "external_source": "open_finance",
        },
    )

    budget = service.create_budget(
        USER_ID,
        BudgetCreate(name="Servicos", amount="100", period_month="2026-07", category_id=category["id"], status="active"),
    )

    assert budget.spent_amount == 80
    assert budget.usage_percent == 80
    assert budget.alert_level == "near_limit"


def test_recurring_suggestions_require_user_confirmation(tmp_path: Path) -> None:
    repository = LocalJsonRepository(tmp_path)
    service = PlanningService(repository)
    for month in ("06", "07"):
        repository.create_transaction(
            USER_ID,
            {
                "account_id": None,
                "card_id": None,
                "card_statement_id": None,
                "transaction_date": f"2026-{month}-05",
                "description": "Spotify Assinatura",
                "original_description": "Spotify Assinatura",
                "amount": "21.90",
                "type": "expense",
                "category_id": None,
                "source_file_id": None,
                "installment_current": None,
                "installment_total": None,
                "status": "confirmed",
            },
        )

    overview = service.overview(USER_ID, period_month="2026-07")

    assert repository.list_recurring_items(USER_ID) == []
    assert overview.recurring_suggestions[0].status == "suggested"
    assert overview.recurring_suggestions[0].kind == "subscription"
    assert overview.recurring_suggestions[0].linked_transaction_count == 2

    service.create_recurring_item(
        USER_ID,
        RecurringItemCreate(
            name=overview.recurring_suggestions[0].name,
            kind=overview.recurring_suggestions[0].kind,
            amount=overview.recurring_suggestions[0].amount,
            cadence="monthly",
            status="ignored",
            source="ai_ignored",
        ),
    )

    assert service.overview(USER_ID, period_month="2026-07").recurring_suggestions == []

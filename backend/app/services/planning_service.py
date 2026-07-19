from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha1
from typing import Any

from app.core.errors import AppError
from app.parsers.utils import normalize_description
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


EXPENSE_TYPES = {"expense", "payment"}


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


def _date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def _month(value: date | None = None) -> str:
    current = value or date.today()
    return f"{current.year:04d}-{current.month:02d}"


def _progress(current: Decimal, target: Decimal) -> Decimal:
    if target <= 0:
        return Decimal("0.00")
    return min((current / target * Decimal("100")).quantize(Decimal("0.01")), Decimal("999.99"))


class PlanningService:
    def __init__(self, repository: Any, ai_planning_analyzer: Any | None = None):
        self.repository = repository
        self.ai_planning_analyzer = ai_planning_analyzer

    def overview(self, user_id: str, period_month: str | None = None) -> PlanningOverview:
        month = period_month or _month()
        return PlanningOverview(
            recurring_items=[self._recurring_read(item) for item in self.repository.list_recurring_items(user_id) if item.get("status") == "active"],
            recurring_suggestions=self._recurring_suggestions(user_id),
            goals=[self._goal_read(item) for item in self.repository.list_financial_goals(user_id)],
            budgets=[self._budget_read(user_id, item) for item in self.repository.list_budgets(user_id, period_month=month)],
        )

    def list_recurring_items(self, user_id: str) -> list[RecurringItemRead]:
        return [self._recurring_read(item) for item in self.repository.list_recurring_items(user_id) if item.get("status") == "active"]

    def create_recurring_item(self, user_id: str, payload: RecurringItemCreate) -> RecurringItemRead:
        data = payload.model_dump(mode="json")
        self._validate_references(user_id, data)
        record = self.repository.create_recurring_item(user_id, data)
        self._link_matching_transactions(user_id, record)
        return self._recurring_read(record)

    def update_recurring_item(self, user_id: str, recurring_item_id: str, payload: RecurringItemUpdate) -> RecurringItemRead:
        data = payload.model_dump(mode="json", exclude_unset=True)
        self._validate_references(user_id, data)
        record = self.repository.update_recurring_item(user_id, recurring_item_id, data)
        if not record:
            raise AppError("Recorrente nao encontrado.", status_code=404, code="recurring_item_not_found")
        self._link_matching_transactions(user_id, record)
        return self._recurring_read(record)

    def delete_recurring_item(self, user_id: str, recurring_item_id: str) -> RecurringItemRead:
        record = self.repository.update_recurring_item(user_id, recurring_item_id, {"status": "inactive"})
        if not record:
            raise AppError("Recorrente nao encontrado.", status_code=404, code="recurring_item_not_found")
        return self._recurring_read(record)

    def list_goals(self, user_id: str) -> list[FinancialGoalRead]:
        return [self._goal_read(item) for item in self.repository.list_financial_goals(user_id)]

    def create_goal(self, user_id: str, payload: FinancialGoalCreate) -> FinancialGoalRead:
        record = self.repository.create_financial_goal(user_id, payload.model_dump(mode="json"))
        return self._goal_read(record)

    def update_goal(self, user_id: str, goal_id: str, payload: FinancialGoalUpdate) -> FinancialGoalRead:
        record = self.repository.update_financial_goal(user_id, goal_id, payload.model_dump(mode="json", exclude_unset=True))
        if not record:
            raise AppError("Meta nao encontrada.", status_code=404, code="financial_goal_not_found")
        return self._goal_read(record)

    def delete_goal(self, user_id: str, goal_id: str) -> FinancialGoalRead:
        record = self.repository.update_financial_goal(user_id, goal_id, {"status": "inactive"})
        if not record:
            raise AppError("Meta nao encontrada.", status_code=404, code="financial_goal_not_found")
        return self._goal_read(record)

    def list_budgets(self, user_id: str, period_month: str | None = None) -> list[BudgetRead]:
        return [self._budget_read(user_id, item) for item in self.repository.list_budgets(user_id, period_month=period_month or _month())]

    def create_budget(self, user_id: str, payload: BudgetCreate) -> BudgetRead:
        data = payload.model_dump(mode="json")
        self._validate_references(user_id, data)
        record = self.repository.create_budget(user_id, data)
        return self._budget_read(user_id, record)

    def update_budget(self, user_id: str, budget_id: str, payload: BudgetUpdate) -> BudgetRead:
        data = payload.model_dump(mode="json", exclude_unset=True)
        self._validate_references(user_id, data)
        record = self.repository.update_budget(user_id, budget_id, data)
        if not record:
            raise AppError("Orçamento não encontrado.", status_code=404, code="budget_not_found")
        return self._budget_read(user_id, record)

    def delete_budget(self, user_id: str, budget_id: str) -> BudgetRead:
        record = self.repository.update_budget(user_id, budget_id, {"status": "inactive"})
        if not record:
            raise AppError("Orçamento não encontrado.", status_code=404, code="budget_not_found")
        return self._budget_read(user_id, record)

    def _validate_references(self, user_id: str, data: dict[str, Any]) -> None:
        category_id = data.get("category_id")
        if category_id and not self.repository.category_exists(category_id, user_id):
            raise AppError("Categoria nao encontrada.", status_code=400, code="category_not_found")
        account_id = data.get("account_id")
        if account_id and not self.repository.get_account(user_id, account_id):
            raise AppError("Conta nao encontrada.", status_code=400, code="account_not_found")
        card_id = data.get("card_id")
        if card_id and not self.repository.get_card(user_id, card_id):
            raise AppError("Cartao nao encontrado.", status_code=400, code="card_not_found")

    def _recurring_read(self, item: dict[str, Any]) -> RecurringItemRead:
        data = dict(item)
        data.pop("linked_transaction_count", None)
        return RecurringItemRead(
            **data,
            linked_transaction_count=self.repository.count_recurring_item_transactions(item["user_id"], item["id"]),
        )

    def _goal_read(self, item: dict[str, Any]) -> FinancialGoalRead:
        target = _money(item.get("target_amount"))
        current = _money(item.get("current_amount"))
        return FinancialGoalRead(
            **item,
            progress_percent=_progress(current, target),
            remaining_amount=max(target - current, Decimal("0.00")),
        )

    def _budget_read(self, user_id: str, item: dict[str, Any]) -> BudgetRead:
        budget_amount = _money(item.get("amount"))
        spent = self._budget_spent(user_id, item)
        usage = _progress(spent, budget_amount)
        alert = "over_limit" if spent > budget_amount else "near_limit" if usage >= Decimal("80.00") else "ok"
        return BudgetRead(
            **item,
            spent_amount=spent,
            remaining_amount=budget_amount - spent,
            usage_percent=usage,
            alert_level=alert,
        )

    def _budget_spent(self, user_id: str, budget: dict[str, Any]) -> Decimal:
        period = str(budget.get("period_month") or _month())
        category_id = budget.get("category_id")
        total = Decimal("0.00")
        for transaction in self.repository.list_transactions(user_id):
            if transaction.get("status") != "confirmed" or transaction.get("type") not in EXPENSE_TYPES:
                continue
            if not str(transaction.get("transaction_date") or "").startswith(period):
                continue
            if category_id and transaction.get("category_id") != category_id:
                continue
            total += _money(transaction.get("amount"))
        return total.quantize(Decimal("0.01"))

    def _recurring_suggestions(self, user_id: str) -> list[RecurringItemRead]:
        existing_names = {normalize_description(item.get("name", "")) for item in self.repository.list_recurring_items(user_id)}
        categories = self.repository.categories(user_id)
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for transaction in self.repository.list_transactions(user_id):
            if transaction.get("type") not in EXPENSE_TYPES:
                continue
            key = (normalize_description(transaction.get("description", "")), str(_money(transaction.get("amount"))))
            if key[0]:
                grouped[key].append(transaction)

        suggestions = []
        for (description_key, amount), items in grouped.items():
            months = sorted({
                (parsed.year, parsed.month)
                for item in items
                if (parsed := _date(item.get("transaction_date")))
            })
            if len(months) < 2 or description_key in existing_names:
                continue
            sample = sorted(items, key=lambda item: item.get("transaction_date", ""), reverse=True)[0]
            name = str(sample.get("description") or description_key).title()
            description_terms = description_key.lower()
            kind = "subscription" if any(term in description_terms for term in ("assinatura", "netflix", "spotify", "openai", "amazon", "icloud")) else "fixed_bill"
            suggestion_key = sha1(f"{description_key}|{amount}".encode("utf-8")).hexdigest()[:12]
            source_counts = Counter(str(item.get("external_source") or item.get("source") or "manual") for item in items)
            suggestions.append(
                {
                    "id": f"suggestion-{suggestion_key}",
                    "user_id": user_id,
                    "name": name,
                    "kind": kind,
                    "amount": amount,
                    "cadence": "monthly",
                    "category_id": sample.get("category_id"),
                    "account_id": sample.get("account_id"),
                    "card_id": sample.get("card_id"),
                    "start_date": sample.get("transaction_date"),
                    "end_date": None,
                    "next_due_date": None,
                    "status": "suggested",
                    "source": "heuristic_suggestion",
                    "notes": "Sugestão baseada em transações semelhantes em meses diferentes.",
                    "metadata": {
                        "transaction_ids": [item["id"] for item in items[:12]],
                        "occurrences": len(items),
                        "months": [f"{year:04d}-{month:02d}" for year, month in months],
                        "sample_descriptions": list(dict.fromkeys(str(item.get("description") or "") for item in items if item.get("description")))[:5],
                        "source_counts": dict(source_counts),
                    },
                    "created_at": datetime.now().isoformat(),
                    "updated_at": None,
                }
            )
        if self.ai_planning_analyzer:
            suggestions = self.ai_planning_analyzer.enrich_recurring_suggestions(suggestions, categories)
        return [RecurringItemRead(**item, linked_transaction_count=len(item["metadata"].get("transaction_ids", []))) for item in suggestions[:10]]

    def _link_matching_transactions(self, user_id: str, recurring_item: dict[str, Any]) -> None:
        if recurring_item.get("status") not in {"active", "suggested"}:
            return
        expected = _money(recurring_item.get("amount"))
        name_key = normalize_description(recurring_item.get("name", ""))
        if not name_key:
            return
        for transaction in self.repository.list_transactions(user_id):
            if transaction.get("type") not in EXPENSE_TYPES:
                continue
            if _money(transaction.get("amount")) != expected:
                continue
            if name_key.split()[0] not in normalize_description(transaction.get("description", "")):
                continue
            self.repository.link_recurring_item_transaction(user_id, recurring_item["id"], transaction["id"])

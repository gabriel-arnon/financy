from decimal import Decimal

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_request_user_id, repository
from app.api.statements import _statement_payload
from app.core.errors import AppError
from app.schemas.accounts import (
    AccountCreate,
    AccountRead,
    AccountSummary,
    AccountSummaryCard,
    AccountUpdate,
    CardCreate,
    CardRead,
    CardSummary,
    CardSummaryStatement,
    CardSummaryTransaction,
    CardUpdate,
)
from app.schemas.statements import CardStatementSummary
from app.schemas.transactions import TransactionRead


accounts_router = APIRouter(prefix="/accounts", tags=["accounts"])
cards_router = APIRouter(prefix="/cards", tags=["cards"])


@accounts_router.get("", response_model=list[AccountRead])
def list_accounts(user_id: str = Depends(get_request_user_id)) -> list[AccountRead]:
    return [AccountRead(**item) for item in repository.list_accounts(user_id)]


@accounts_router.get("/{account_id}/summary", response_model=AccountSummary)
def get_account_summary(
    account_id: str,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    user_id: str = Depends(get_request_user_id),
) -> AccountSummary:
    account = repository.get_account(user_id, account_id)
    if not account or account.get("status") != "active":
        raise AppError("Conta nao encontrada.", status_code=404, code="account_not_found")

    linked_cards = [card for card in repository.list_cards(user_id) if card.get("account_id") == account_id]
    linked_card_ids = {card["id"] for card in linked_cards}

    open_statement_payloads = [
        _statement_payload(user_id, statement)
        for statement in repository.list_card_statements(user_id)
        if statement.get("card_id") in linked_card_ids and statement.get("status", "open") in {"open", "overdue"}
    ]
    open_statements = [CardStatementSummary(**item) for item in open_statement_payloads]

    def statement_amount(item: dict) -> Decimal:
        return Decimal(str(item["reported_total"] if item.get("reported_total") is not None else item.get("calculated_total", "0")))

    total_open_statements = sum((statement_amount(item) for item in open_statement_payloads), Decimal("0"))
    total_open_statements_warning = sum(
        (statement_amount(item) for item in open_statement_payloads if item.get("integrity_status") == "no_transactions"),
        Decimal("0"),
    )
    total_open_statements_ok = total_open_statements - total_open_statements_warning

    transactions = [
        transaction
        for transaction in repository.list_transactions(user_id)
        if transaction.get("account_id") == account_id or transaction.get("card_id") in linked_card_ids
    ]
    period_transactions = [
        transaction
        for transaction in transactions
        if (not start_date or transaction.get("transaction_date", "") >= start_date)
        and (not end_date or transaction.get("transaction_date", "") <= end_date)
    ]

    total_income = sum(
        (
            Decimal(str(transaction.get("amount", "0")))
            for transaction in period_transactions
            if transaction.get("type") in {"income", "refund"}
        ),
        Decimal("0"),
    )
    total_expense = sum(
        (
            Decimal(str(transaction.get("amount", "0")))
            for transaction in period_transactions
            if transaction.get("type") == "expense"
        ),
        Decimal("0"),
    )
    recent_transactions = sorted(
        period_transactions,
        key=lambda item: (item.get("transaction_date", ""), item.get("created_at", "")),
        reverse=True,
    )[:10]

    summary_cards = []
    for card in linked_cards:
        card_statements = [item for item in open_statement_payloads if item.get("card_id") == card["id"]]
        card_total = sum(
            (
                Decimal(str(item["reported_total"] if item.get("reported_total") is not None else item.get("calculated_total", "0")))
                for item in card_statements
            ),
            Decimal("0"),
        )
        summary_cards.append(
            AccountSummaryCard(
                **card,
                open_statement_count=len(card_statements),
                open_statement_total=card_total,
            )
        )

    return AccountSummary(
        account=AccountRead(**account),
        cards=summary_cards,
        open_statements=sorted(open_statements, key=lambda item: item.due_date or item.created_at.isoformat(), reverse=True),
        total_open_statements=total_open_statements,
        total_open_statements_ok=total_open_statements_ok,
        total_open_statements_warning=total_open_statements_warning,
        transaction_count=len(period_transactions),
        total_income=total_income,
        total_expense=total_expense,
        net_balance_period=total_income - total_expense,
        recent_transactions=[TransactionRead(**item) for item in recent_transactions],
    )


@accounts_router.post("", response_model=AccountRead)
def create_account(payload: AccountCreate, user_id: str = Depends(get_request_user_id)) -> AccountRead:
    record = repository.create_account(user_id, payload.model_dump(mode="json"))
    return AccountRead(**record)


@accounts_router.put("/{account_id}", response_model=AccountRead)
def update_account(account_id: str, payload: AccountUpdate, user_id: str = Depends(get_request_user_id)) -> AccountRead:
    record = repository.update_account(user_id, account_id, payload.model_dump(mode="json", exclude_unset=True))
    if not record:
        raise AppError("Conta nao encontrada.", status_code=404, code="account_not_found")
    return AccountRead(**record)


@accounts_router.delete("/{account_id}", response_model=AccountRead)
def delete_account(account_id: str, user_id: str = Depends(get_request_user_id)) -> AccountRead:
    linked_active_cards = [card for card in repository.list_cards(user_id) if card.get("account_id") == account_id]
    if linked_active_cards:
        raise AppError(
            "Não é possível inativar conta com cartões ativos vinculados.",
            status_code=400,
            code="account_has_active_cards",
        )
    record = repository.delete_account(user_id, account_id)
    if not record:
        raise AppError("Conta nao encontrada.", status_code=404, code="account_not_found")
    return AccountRead(**record)


def validate_card_account(user_id: str, account_id: str | None) -> None:
    if not account_id:
        raise AppError("Cartão deve estar vinculado a uma conta ativa.", status_code=400, code="card_account_required")
    account = repository.get_account(user_id, account_id)
    if not account:
        raise AppError("Conta vinculada ao cartao nao encontrada.", status_code=400, code="card_account_not_found")
    if account.get("status") != "active":
        raise AppError("Cartão deve estar vinculado a uma conta ativa.", status_code=400, code="card_account_inactive")


@cards_router.get("", response_model=list[CardRead])
def list_cards(user_id: str = Depends(get_request_user_id)) -> list[CardRead]:
    return [CardRead(**item) for item in repository.list_cards(user_id)]


@cards_router.get("/{card_id}/summary", response_model=CardSummary)
def get_card_summary(card_id: str, user_id: str = Depends(get_request_user_id)) -> CardSummary:
    card = repository.get_card(user_id, card_id)
    if not card or card.get("status") != "active":
        raise AppError("Cartao nao encontrado.", status_code=404, code="card_not_found")

    account = repository.get_account(user_id, card["account_id"])
    if not account or account.get("status") != "active":
        raise AppError("Conta vinculada ao cartao nao encontrada.", status_code=404, code="card_account_not_found")

    statement_payloads = [
        _statement_payload(user_id, statement)
        for statement in repository.list_card_statements(user_id)
        if statement.get("card_id") == card_id
    ]

    def statement_amount(item: dict) -> Decimal:
        return Decimal(str(item["reported_total"] if item.get("reported_total") is not None else item.get("calculated_total", "0")))

    open_statement_payloads = [
        item for item in statement_payloads if item.get("status", "open") in {"open", "overdue"}
    ]
    limit_used = sum((statement_amount(item) for item in open_statement_payloads), Decimal("0"))
    limit_total = Decimal(str(card["limit_amount"])) if card.get("limit_amount") not in (None, "") else None
    limit_available = None
    usage_percent = None
    if limit_total is not None and limit_total != Decimal("0"):
        limit_available = limit_total - limit_used
        usage_percent = (limit_used / limit_total * Decimal("100")).quantize(Decimal("0.01"))

    def to_statement(item: dict) -> CardSummaryStatement:
        return CardSummaryStatement(
            id=item["id"],
            reference_month=item["reference_month"],
            due_date=item.get("due_date"),
            status=item["status"],
            reported_total=item.get("reported_total"),
            calculated_total=item["calculated_total"],
            difference=item.get("difference"),
            integrity_status=item["integrity_status"],
            transaction_count=item["transaction_count"],
        )

    upcoming = sorted(
        open_statement_payloads,
        key=lambda item: (item.get("due_date") is None, item.get("due_date") or "", item.get("created_at", "")),
    )
    history = sorted(
        statement_payloads,
        key=lambda item: (item.get("reference_month") or "", item.get("created_at", "")),
        reverse=True,
    )[:12]

    transactions = [
        transaction for transaction in repository.list_transactions(user_id) if transaction.get("card_id") == card_id
    ]
    recent_transactions = sorted(
        transactions,
        key=lambda item: (item.get("transaction_date", ""), item.get("created_at", "")),
        reverse=True,
    )[:20]

    return CardSummary(
        card=CardRead(**card),
        account=AccountRead(**account),
        limit_total=limit_total,
        limit_used=limit_used,
        limit_available=limit_available,
        usage_percent=usage_percent,
        upcoming_statements=[to_statement(item) for item in upcoming],
        statement_history=[to_statement(item) for item in history],
        recent_transactions=[CardSummaryTransaction(**item) for item in recent_transactions],
    )


@cards_router.post("", response_model=CardRead)
def create_card(payload: CardCreate, user_id: str = Depends(get_request_user_id)) -> CardRead:
    validate_card_account(user_id, payload.account_id)
    record = repository.create_card(user_id, payload.model_dump(mode="json"))
    return CardRead(**record)


@cards_router.put("/{card_id}", response_model=CardRead)
def update_card(card_id: str, payload: CardUpdate, user_id: str = Depends(get_request_user_id)) -> CardRead:
    if "account_id" in payload.model_fields_set:
        validate_card_account(user_id, payload.account_id)
    record = repository.update_card(user_id, card_id, payload.model_dump(mode="json", exclude_unset=True))
    if not record:
        raise AppError("Cartao nao encontrado.", status_code=404, code="card_not_found")
    return CardRead(**record)


@cards_router.delete("/{card_id}", response_model=CardRead)
def delete_card(card_id: str, user_id: str = Depends(get_request_user_id)) -> CardRead:
    record = repository.delete_card(user_id, card_id)
    if not record:
        raise AppError("Cartao nao encontrado.", status_code=404, code="card_not_found")
    return CardRead(**record)

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_request_user_id, repository
from app.core.errors import AppError
from app.schemas.statements import CardStatementDetail, CardStatementStatusUpdate, CardStatementSummary
from app.schemas.transactions import TransactionRead


router = APIRouter(prefix="/statements", tags=["statements"])
_MISSING = object()


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _statement_payload(
    user_id: str,
    statement: dict[str, Any],
    card: dict[str, Any] | None | object = _MISSING,
    transactions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    card = repository.get_card(user_id, statement["card_id"]) if card is _MISSING else card
    transactions = transactions if transactions is not None else repository.list_transactions_by_statement(user_id, statement["id"])
    calculated_total = sum((Decimal(str(item.get("amount", "0"))) for item in transactions), Decimal("0"))
    reported_total = _decimal(statement.get("total_amount"))
    difference = reported_total - calculated_total if reported_total is not None else None
    if len(transactions) == 0:
        integrity_status = "no_transactions"
        integrity_label = "Sem transações"
    elif difference is not None and difference != Decimal("0"):
        integrity_status = "difference"
        integrity_label = "Divergência"
    else:
        integrity_status = "ok"
        integrity_label = "OK"
    return {
        "id": statement["id"],
        "user_id": statement["user_id"],
        "card_id": statement["card_id"],
        "account_id": card.get("account_id") if card else None,
        "reference_month": statement["reference_month"],
        "due_date": statement.get("due_date"),
        "closing_date": statement.get("closing_date"),
        "reported_total": reported_total,
        "minimum_payment_amount": _decimal(statement.get("minimum_payment_amount")),
        "status": statement.get("status", "open"),
        "paid_at": statement.get("paid_at"),
        "source_file_id": statement.get("source_file_id"),
        "transaction_count": len(transactions),
        "calculated_total": calculated_total,
        "difference": difference,
        "integrity_status": integrity_status,
        "integrity_label": integrity_label,
        "created_at": statement["created_at"],
    }


@router.get("", response_model=list[CardStatementSummary])
def list_statements(user_id: str = Depends(get_request_user_id)) -> list[CardStatementSummary]:
    statements = repository.list_card_statements(user_id)
    cards_by_id = {card["id"]: card for card in repository.list_cards(user_id)}
    transactions_by_statement: dict[str, list[dict[str, Any]]] = {}
    for transaction in repository.list_transactions(user_id):
        statement_id = transaction.get("card_statement_id")
        if statement_id:
            transactions_by_statement.setdefault(statement_id, []).append(transaction)
    payloads = [
        _statement_payload(
            user_id,
            statement,
            cards_by_id.get(statement["card_id"]),
            transactions_by_statement.get(statement["id"], []),
        )
        for statement in statements
    ]
    return [CardStatementSummary(**item) for item in sorted(payloads, key=lambda item: item.get("due_date") or "", reverse=True)]


@router.get("/{statement_id}", response_model=CardStatementDetail)
def get_statement(statement_id: str, user_id: str = Depends(get_request_user_id)) -> CardStatementDetail:
    statement = repository.get_card_statement(user_id, statement_id)
    if not statement:
        raise AppError("Fatura nao encontrada.", status_code=404, code="statement_not_found")
    payload = _statement_payload(user_id, statement)
    payload["transactions"] = [
        TransactionRead(**item) for item in repository.list_transactions_by_statement(user_id, statement_id)
    ]
    return CardStatementDetail(**payload)


@router.delete("/{statement_id}")
def delete_statement(statement_id: str, user_id: str = Depends(get_request_user_id)) -> dict[str, str]:
    statement = repository.get_card_statement(user_id, statement_id)
    if not statement:
        raise AppError("Fatura nao encontrada.", status_code=404, code="statement_not_found")

    transactions = repository.list_transactions_by_statement(user_id, statement_id)
    if transactions:
        raise AppError(
            "Não é possível excluir fatura com transações vinculadas.",
            status_code=400,
            code="statement_has_transactions",
        )

    if not repository.delete_card_statement(user_id, statement_id):
        raise AppError("Fatura nao encontrada.", status_code=404, code="statement_not_found")
    return {"status": "deleted"}


@router.patch("/{statement_id}/status", response_model=CardStatementDetail)
def update_statement_status(
    statement_id: str,
    payload: CardStatementStatusUpdate,
    user_id: str = Depends(get_request_user_id),
) -> CardStatementDetail:
    if not repository.get_card_statement(user_id, statement_id):
        raise AppError("Fatura nao encontrada.", status_code=404, code="statement_not_found")

    paid_at = None
    if payload.status == "paid":
        paid_at = (payload.paid_at or datetime.now(timezone.utc)).isoformat()

    updated = repository.update_card_statement(
        user_id,
        statement_id,
        {
            "status": payload.status,
            "paid_at": paid_at,
        },
    )
    if not updated:
        raise AppError("Fatura nao encontrada.", status_code=404, code="statement_not_found")

    response = _statement_payload(user_id, updated)
    response["transactions"] = [
        TransactionRead(**item) for item in repository.list_transactions_by_statement(user_id, statement_id)
    ]
    return CardStatementDetail(**response)

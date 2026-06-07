from pathlib import Path

from ofxparse import OfxParser

from app.models.enums import TransactionType
from app.schemas.common import NormalizedTransactionPreview


def parse(path: Path, mime_type: str | None = None) -> list[NormalizedTransactionPreview]:
    with path.open("rb") as handle:
        ofx = OfxParser.parse(handle)

    previews: list[NormalizedTransactionPreview] = []
    account = ofx.account
    for transaction in account.statement.transactions:
        description = transaction.memo or transaction.payee or transaction.id
        amount = transaction.amount
        previews.append(
            NormalizedTransactionPreview(
                transaction_date=transaction.date.date(),
                description=description.strip(),
                original_description=description.strip(),
                amount=abs(amount),
                type=TransactionType.income if amount > 0 else TransactionType.expense,
                raw_row={"id": transaction.id, "type": transaction.type},
                parser_confidence=0.95,
            )
        )
    return previews

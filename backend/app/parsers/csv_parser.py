import csv
from pathlib import Path

from app.models.enums import TransactionType
from app.schemas.common import NormalizedTransactionPreview, ParserResult
from app.parsers.utils import infer_transaction_type, parse_brazilian_money, parse_date


DATE_KEYS = ("date", "data", "transaction_date")
DESCRIPTION_KEYS = ("description", "descricao", "descrição", "historico", "histórico")
AMOUNT_KEYS = ("amount", "valor", "value")


def _first(row: dict[str, str], keys: tuple[str, ...]) -> str | None:
    normalized = {key.strip().lower(): value for key, value in row.items()}
    for key in keys:
        if key in normalized and normalized[key]:
            return normalized[key]
    return None


def parse(path: Path, mime_type: str | None = None) -> ParserResult:
    previews: list[NormalizedTransactionPreview] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            raw_date = _first(row, DATE_KEYS)
            description = _first(row, DESCRIPTION_KEYS)
            raw_amount = _first(row, AMOUNT_KEYS)
            if not raw_date or not description or not raw_amount:
                continue
            amount = parse_brazilian_money(raw_amount)
            previews.append(
                NormalizedTransactionPreview(
                    transaction_date=parse_date(raw_date),
                    description=description.strip(),
                    original_description=description.strip(),
                    amount=abs(amount),
                    type=TransactionType(infer_transaction_type(description, amount)),
                    raw_row=row,
                    parser_confidence=0.9,
                )
            )
    return ParserResult(items=previews)

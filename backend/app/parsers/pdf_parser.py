import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pdfplumber

from app.models.enums import TransactionType
from app.schemas.common import NormalizedTransactionPreview
from app.parsers.utils import detect_installment, infer_transaction_type, parse_brazilian_money


IGNORED_KEYWORDS = (
    "saldo anterior",
    "subtotal",
    "total da fatura",
    "pagamento da fatura",
    "pagamento recebido",
    "limite disponivel",
    "encargos",
    "juros",
    "iof",
    "mensagem",
    "informativo",
    "ouvidoria",
    "central de atendimento",
    "sac banco do brasil",
)

LINE_RE = re.compile(
    r"^(?P<date>\d{2}/\d{2}(?:/\d{2,4})?)\s+(?P<description>.+?)\s+(?P<amount>-?(?:R\$\s*)?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+,\d{2})$",
    re.IGNORECASE,
)


def _should_ignore(line: str) -> bool:
    lowered = line.lower()
    return any(keyword in lowered for keyword in IGNORED_KEYWORDS)


def _parse_date(value: str, fallback_year: int) -> date:
    parts = value.split("/")
    day = int(parts[0])
    month = int(parts[1])
    year = fallback_year
    if len(parts) == 3:
        raw_year = int(parts[2])
        year = 2000 + raw_year if raw_year < 100 else raw_year
    return date(year, month, day)


def _statement_year(text: str) -> int:
    match = re.search(r"(?:vencimento|referencia|fechamento).{0,30}(\d{2}/\d{2}/(?P<year>\d{4}))", text, re.IGNORECASE)
    if match:
        return int(match.group("year"))
    return date.today().year


def _extract_text(path: Path) -> str:
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
            pages.append(page_text)
            for table in page.extract_tables() or []:
                for row in table:
                    cleaned = " ".join(cell.strip() for cell in row if cell and cell.strip())
                    if cleaned:
                        pages.append(cleaned)
    return "\n".join(pages)


def parse(path: Path, mime_type: str | None = None) -> list[NormalizedTransactionPreview]:
    text = _extract_text(path)
    fallback_year = _statement_year(text)
    previews: list[NormalizedTransactionPreview] = []

    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line or _should_ignore(line):
            continue

        match = LINE_RE.match(line)
        if not match:
            continue

        description = match.group("description").strip(" -")
        if _should_ignore(description):
            continue

        amount = parse_brazilian_money(match.group("amount"))
        installment_current, installment_total = detect_installment(description)
        tx_type = TransactionType(infer_transaction_type(description, amount))
        normalized_amount = abs(amount) if tx_type == TransactionType.expense else amount

        previews.append(
            NormalizedTransactionPreview(
                transaction_date=_parse_date(match.group("date"), fallback_year),
                description=description,
                original_description=description,
                amount=Decimal(normalized_amount),
                type=tx_type,
                installment_current=installment_current,
                installment_total=installment_total,
                raw_text=line,
                raw_row={"line": line},
                parser_confidence=0.82 if installment_total else 0.78,
                needs_review=False,
            )
        )

    return previews

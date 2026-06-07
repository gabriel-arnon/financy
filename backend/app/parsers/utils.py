import re
import unicodedata
from datetime import date
from decimal import Decimal

from dateutil import parser as date_parser


MONEY_RE = re.compile(r"(?P<sign>-)?(?:R\$\s*)?(?P<number>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})")


def normalize_description(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().upper()


def parse_brazilian_money(value: str) -> Decimal:
    match = MONEY_RE.search(value)
    if not match:
        raise ValueError(f"Invalid money value: {value}")
    number = match.group("number").replace(".", "").replace(",", ".")
    amount = Decimal(number)
    if match.group("sign"):
        return -amount
    return amount


def parse_date(value: str, default_year: int | None = None) -> date:
    parsed = date_parser.parse(value, dayfirst=True, fuzzy=True)
    if default_year and parsed.year == date.today().year and not re.search(r"\d{4}", value):
        return parsed.replace(year=default_year).date()
    return parsed.date()


def detect_installment(description: str) -> tuple[int | None, int | None]:
    match = re.search(r"(?P<current>\d{1,2})\s*/\s*(?P<total>\d{1,2})", description)
    if not match:
        return None, None
    return int(match.group("current")), int(match.group("total"))


def infer_transaction_type(description: str, amount: Decimal) -> str:
    text = normalize_description(description)
    if "PAGAMENTO" in text:
        return "payment"
    if amount < 0 or "ESTORNO" in text or "CREDITO" in text:
        return "refund"
    return "expense"

import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pdfplumber

from app.models.enums import ExcludedReason, TransactionType
from app.parsers.utils import detect_installment, normalize_description, parse_brazilian_money
from app.schemas.common import IgnoredPdfLine, NormalizedTransactionPreview, ParserResult, StatementMetadata


SECTION_ALIASES = {
    "lancamentos nesta fatura": None,
    "lancamentos": None,
    "restaurantes": "Restaurantes",
    "servicos": "Serviços",
    "supermercados": "Supermercados",
    "vestuario": "Vestuário",
    "outros lancamentos": "Outros lançamentos",
    "compras parceladas": "Compras parceladas",
}

COUNTRY_CODES = {
    "ARG",
    "BRA",
    "BR",
    "BRASIL",
    "BRAZIL",
    "CA",
    "CHL",
    "ESP",
    "EUA",
    "FRA",
    "GBR",
    "USA",
    "URY",
}

CARD_BRANDS = {
    "ELO": "Elo",
    "VISA": "Visa",
    "MASTERCARD": "Mastercard",
    "MAESTRO": "Maestro",
    "AMEX": "Amex",
    "AMERICAN EXPRESS": "American Express",
    "HIPERCARD": "Hipercard",
}

INSTITUTION_ALIASES = {
    "BANCO DO BRASIL": "Banco do Brasil",
    "BB": "Banco do Brasil",
    "ITAU": "Itaú",
    "ITAÚ": "Itaú",
    "BRADESCO": "Bradesco",
    "SANTANDER": "Santander",
    "CAIXA": "Caixa",
    "NUBANK": "Nubank",
    "INTER": "Banco Inter",
    "MERCADO PAGO": "Mercado Pago",
    "PICPAY": "PicPay",
}

INFORMATIVE_KEYWORDS = (
    "limite disponivel",
    "encargos",
    "juros",
    "mensagem",
    "informativo",
    "ouvidoria",
    "central de atendimento",
    "sac banco do brasil",
    "cet",
)

LINE_RE = re.compile(
    r"^(?P<date>\d{2}/\d{2}(?:/\d{2,4})?)\s+"
    r"(?P<body>.+)\s+"
    r"(?P<amount>-?(?:R\$\s*)?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+,\d{2})$",
    re.IGNORECASE,
)

DATE_AMOUNT_RE = re.compile(
    r"^(?P<date>\d{2}/\d{2}(?:/\d{2,4})?).*"
    r"(?P<amount>-?(?:R\$\s*)?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+,\d{2})$",
    re.IGNORECASE,
)

CAIXA_CARD_TRANSACTION_RE = re.compile(
    r"^(?:.*?\s)?(?P<date>\d{2}/\d{2})\s+"
    r"(?P<body>.+?)\s+"
    r"(?P<amount>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})(?P<sign>[DC])$",
    re.IGNORECASE,
)

CAIXA_CARD_BLOCK_RE = re.compile(r"\(CARTAO\s+(?P<digits>\d{4})\)", re.IGNORECASE)

BANK_STATEMENT_TRANSACTION_RE = re.compile(
    r"^(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<body>.*?)\s+(?P<amount>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})\s+\((?P<sign>[+-])\)$"
)

BANK_STATEMENT_HISTORY_HEADINGS = {
    "PAGTO CARTAO CREDITO",
    "PAGAMENTO DE BOLETO",
    "PIX - ENVIADO",
    "PIX - RECEBIDO",
    "PIX AGENDADO",
    "TRANSFERENCIA RECEBIDA",
}

MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "março": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

SHORT_MONTHS = {
    "jan": 1,
    "fev": 2,
    "mar": 3,
    "abr": 4,
    "mai": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "set": 9,
    "out": 10,
    "nov": 11,
    "dez": 12,
}

INTER_CARD_BLOCK_RE = re.compile(r"^CART[AÃ]O\s+\d{4}\*+(?P<digits>\d{4})", re.IGNORECASE)
INTER_CARD_TRANSACTION_RE = re.compile(
    r"^(?P<day>\d{1,2})\s+de\s+(?P<month>[A-Za-zÃ§Ã‡]{3,})\.?\s+(?P<year>\d{4})\s+"
    r"(?P<body>.+?)\s+-\s+(?P<sign>\+)?\s*R\$\s*(?P<amount>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})$",
    re.IGNORECASE,
)
MERCADO_PAGO_CARD_BLOCK_RE = re.compile(r"Cart[aÃ]o\s+(?P<brand>[A-Za-z]+)\s+\[\*+(?P<digits>\d{4})\]", re.IGNORECASE)
MERCADO_PAGO_TRANSACTION_RE = re.compile(
    r"^(?P<date>\d{2}/\d{2})\s+(?P<body>.+?)\s+R\$\s*(?P<amount>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})$",
    re.IGNORECASE,
)
MERCADO_PAGO_INSTALLMENT_RE = re.compile(r"\s+Parcela\s+(?P<current>\d{1,2})\s+de\s+(?P<total>\d{1,2})\s*$", re.IGNORECASE)


def _clean(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _section_for(line: str) -> str | None:
    normalized = normalize_description(line).lower()
    normalized = normalized.replace("ç", "c")
    for key, section in SECTION_ALIASES.items():
        if normalized == key or normalized.startswith(key):
            return section
    return None


def _is_section_header(line: str) -> bool:
    normalized = normalize_description(line).lower()
    return any(normalized == key or normalized.startswith(key) for key in SECTION_ALIASES)


def _ignored_reason(line: str) -> ExcludedReason | None:
    normalized = normalize_description(line).lower()
    if "saldo anterior" in normalized or "saldo fatura anterior" in normalized:
        return ExcludedReason.saldo_anterior
    if "subtotal" in normalized:
        return ExcludedReason.subtotal
    if "total da fatura" in normalized or "total fatura" in normalized:
        return ExcludedReason.total
    if any(keyword in normalized for keyword in INFORMATIVE_KEYWORDS):
        return ExcludedReason.informativo
    return None


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
    match = re.search(r"(?:vencimento|referencia|referência|fechamento).{0,40}\d{2}/\d{2}/(?P<year>\d{4})", text, re.IGNORECASE)
    if match:
        return int(match.group("year"))
    month_year = re.search(r"(?:referencia|referência).{0,30}(?P<month>\d{2})/(?P<year>\d{4})", text, re.IGNORECASE)
    if month_year:
        return int(month_year.group("year"))
    return date.today().year


def _extract_text(path: Path) -> str:
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
            if page_text.strip():
                pages.append(page_text)
                continue
            for table in page.extract_tables() or []:
                for row in table:
                    cleaned = " ".join(cell.strip() for cell in row if cell and cell.strip())
                    if cleaned:
                        pages.append(cleaned)
    return "\n".join(pages)


def _is_bank_statement(text: str) -> bool:
    normalized = normalize_description(text)
    return "EXTRATO DE CONTA CORRENTE" in normalized and "AGENCIA" in normalized and "CONTA" in normalized


def _is_caixa_card_statement(text: str) -> bool:
    normalized = normalize_description(text)
    return (
        "CARTOES CAIXA" in normalized
        or "CENTRAL DE ATENDIMENTO CARTOES CAIXA" in normalized
        or ("VALOR TOTAL DESTA FATURA" in normalized and "CARTAO" in normalized and "CAIXA" in normalized)
    )


def _is_inter_card_statement(text: str) -> bool:
    normalized = normalize_description(text)
    return "DESPESAS DA FATURA" in normalized and "CARTAO" in normalized and (" INTER" in f" {normalized}" or "BANCO INTER" in normalized)


def _is_mercado_pago_card_statement(text: str) -> bool:
    normalized = normalize_description(text)
    return "MERCADO PAGO" in normalized and "DETALHES DE CONSUMO" in normalized and "CARTAO VISA" in normalized


def _bank_statement_metadata(text: str) -> StatementMetadata:
    metadata = StatementMetadata(account_institution="Banco do Brasil")
    header = re.search(
        r"Per[ií]odo:\s*(?P<period>.+?)\s+Ag[eê]ncia:\s*(?P<agency>[\d-]+)\s+Conta:\s*(?P<account>[\d\w-]+)",
        text,
        re.IGNORECASE,
    )
    if header:
        metadata.account_agency = header.group("agency")
        metadata.account_number = header.group("account")

    final_balance = None
    for raw_line in text.splitlines():
        line = _clean(raw_line)
        if "S A L D O" in normalize_description(line) or normalize_description(line).startswith("SALDO DO DIA"):
            match = re.search(r"(?P<amount>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})\s+\((?P<sign>[+-])\)", line)
            if match:
                amount = parse_brazilian_money(match.group("amount"))
                final_balance = amount if match.group("sign") == "+" else -amount
    metadata.account_balance = final_balance
    return metadata


def _bank_statement_type(description: str, sign: str) -> TransactionType:
    normalized = normalize_description(description)
    if "PAGTO CARTAO" in normalized or "PAGAMENTO DE BOLETO" in normalized:
        return TransactionType.payment
    if "TRANSFERENCIA" in normalized or "PIX" in normalized:
        return TransactionType.income if sign == "+" else TransactionType.transfer
    return TransactionType.income if sign == "+" else TransactionType.expense


def _is_bank_statement_history_heading(line: str) -> bool:
    normalized = normalize_description(line)
    return normalized in BANK_STATEMENT_HISTORY_HEADINGS


def _is_bank_statement_ignored_line(line: str) -> bool:
    normalized = normalize_description(line)
    if not normalized:
        return True
    return (
        normalized.startswith("EXTRATO DE CONTA CORRENTE")
        or normalized.startswith("CLIENTE ")
        or normalized.startswith("PERIODO:")
        or normalized == "LANCAMENTOS"
        or normalized.startswith("DIA LOTE DOCUMENTO")
        or "SALDO ANTERIOR" in normalized
        or normalized.startswith("SALDO DO DIA")
        or "S A L D O" in normalized
        or normalized.startswith("TOTAL APLICACOES FINANCEIRAS")
        or normalized.startswith("* SALDOS POR DIA")
        or normalized.startswith("SUJEITOS A CONFIRMACAO")
    )


def _parse_bank_statement(text: str) -> ParserResult:
    metadata = _bank_statement_metadata(text)
    lines = [_clean(line) for line in text.splitlines() if _clean(line)]
    previews: list[NormalizedTransactionPreview] = []
    ignored_lines: list[IgnoredPdfLine] = []
    current_history: str | None = None
    pending_item: NormalizedTransactionPreview | None = None

    for line in lines:
        if _is_bank_statement_ignored_line(line):
            ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.informativo))
            pending_item = None
            continue

        match = BANK_STATEMENT_TRANSACTION_RE.match(line)
        if match:
            body = match.group("body").strip()
            tokens = body.split()
            lote = tokens[0] if tokens and tokens[0].isdigit() else None
            document = tokens[1] if len(tokens) > 1 and tokens[1].isdigit() else None
            details = " ".join(tokens[2:] if lote and document else tokens)
            description_parts = [part for part in [current_history, details] if part]
            description = " ".join(description_parts).strip() or "Lançamento bancário"
            sign = match.group("sign")
            amount = parse_brazilian_money(match.group("amount"))
            tx_type = _bank_statement_type(description, sign)
            preview = NormalizedTransactionPreview(
                transaction_date=_parse_date(match.group("date"), date.today().year),
                description=description,
                original_description=description,
                amount=amount,
                type=tx_type,
                account_id=None,
                raw_text=line,
                raw_row={
                    "line": line,
                    "history": current_history,
                    "details": details,
                    "lote": lote,
                    "document": document,
                    "parser": "bb_checking_statement_line_v1",
                },
                parser_confidence=0.9 if current_history else 0.78,
                needs_review=False if current_history else True,
                default_selected=tx_type != TransactionType.payment,
                excluded_reason=ExcludedReason.payment if tx_type == TransactionType.payment else None,
                account_institution=metadata.account_institution,
                account_agency=metadata.account_agency,
                account_number=metadata.account_number,
                account_balance=metadata.account_balance,
            )
            previews.append(preview)
            pending_item = preview
            current_history = None
            continue

        if pending_item and not re.match(r"^\d{2}/\d{2}/\d{4}\b", line) and not _is_bank_statement_history_heading(line):
            pending_item.description = f"{pending_item.description} {line}".strip()
            pending_item.original_description = pending_item.description
            if pending_item.raw_row is not None:
                pending_item.raw_row["complement"] = line
            pending_item = None
            continue

        current_history = line
        pending_item = None

    return ParserResult(items=previews, ignored_lines=ignored_lines, statement_metadata=metadata)


def _extract_card_limit(text: str) -> Decimal | None:
    money_pattern = r"(?:R\$\s*)?\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}"
    for raw_line in text.splitlines():
        line = _clean(raw_line)
        normalized = normalize_description(line)
        if not normalized.startswith("LIMITE UNICO"):
            continue
        if "UTILIZADO" in normalized or "DISPONIVEL" in normalized:
            continue
        match = re.search(rf"(?P<amount>{money_pattern})", line, re.IGNORECASE)
        if match:
            return parse_brazilian_money(match.group("amount"))

    match = re.search(
        rf"(?:limite total|limite do cart[aã]o|limite de cr[eé]dito|limite aprovado|limite [uú]nico).{{0,40}}?(?P<amount>{money_pattern})",
        text,
        re.IGNORECASE,
    )
    if match:
        return parse_brazilian_money(match.group("amount"))
    return None


def _extract_caixa_card_limit(text: str) -> Decimal | None:
    money_pattern = r"(?:R\$\s*)?\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}"
    for raw_line in text.splitlines():
        line = _clean(raw_line)
        normalized = normalize_description(line)
        if re.match(r"^TOTAL\s+R\$", line, re.IGNORECASE):
            match = re.search(rf"(?P<amount>{money_pattern})", line, re.IGNORECASE)
            if match:
                return parse_brazilian_money(match.group("amount"))
    return None


def _statement_metadata(text: str, fallback_year: int) -> StatementMetadata:
    metadata = StatementMetadata()

    total_match = re.search(
        r"(?:total da fatura|total fatura|valor total).{0,30}?(?P<amount>(?:R\$\s*)?\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
        text,
        re.IGNORECASE,
    )
    if total_match:
        metadata.statement_total_amount = parse_brazilian_money(total_match.group("amount"))

    metadata.card_limit_amount = _extract_card_limit(text)

    due_match = re.search(r"(?:vencimento|data de vencimento).{0,30}(?P<date>\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    if due_match:
        metadata.statement_due_date = _parse_date(due_match.group("date"), fallback_year)
    else:
        lines = [_clean(line) for line in text.splitlines() if _clean(line)]
        for index, line in enumerate(lines[:-1]):
            if normalize_description(line) in {"VENCIMENTO", "DATA DE VENCIMENTO"}:
                for candidate in lines[index + 1 : index + 4]:
                    next_date = re.search(r"(?P<date>\d{2}/\d{2}/\d{4})", candidate)
                    if next_date:
                        metadata.statement_due_date = _parse_date(next_date.group("date"), fallback_year)
                        break
                if metadata.statement_due_date:
                    break

    ref_numeric = re.search(r"(?:referencia|referência|m[eê]s de referencia).{0,30}(?P<month>\d{2})/(?P<year>\d{4})", text, re.IGNORECASE)
    if ref_numeric:
        metadata.statement_reference_month = date(int(ref_numeric.group("year")), int(ref_numeric.group("month")), 1)
    else:
        ref_named = re.search(
            r"(?:referencia|referência|m[eê]s de referencia).{0,30}(?P<month>[A-Za-zçÇ]+)[/\s-]+(?P<year>\d{4})",
            text,
            re.IGNORECASE,
        )
        if ref_named:
            month = MONTHS.get(ref_named.group("month").lower())
            if month:
                metadata.statement_reference_month = date(int(ref_named.group("year")), month, 1)
    if metadata.statement_reference_month is None and metadata.statement_due_date:
        saldo_month = re.search(
            r"\b(?P<month>janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b\s+saldo fatura anterior",
            text,
            re.IGNORECASE,
        )
        if saldo_month:
            month = MONTHS.get(saldo_month.group("month").lower())
            if month:
                metadata.statement_reference_month = date(metadata.statement_due_date.year, month, 1)

    card_match = re.search(r"(?:cart[aã]o|final).{0,30}(?P<digits>\d{4})", text, re.IGNORECASE)
    if card_match:
        metadata.card_last_digits = card_match.group("digits")

    normalized_text = normalize_description(text)
    for institution_key, institution_label in INSTITUTION_ALIASES.items():
        if institution_key in normalized_text:
            metadata.card_institution = institution_label
            break

    for brand_key, brand_label in CARD_BRANDS.items():
        if brand_key in normalized_text:
            metadata.card_brand = brand_label
            break

    lines = [_clean(line) for line in text.splitlines() if _clean(line)]
    for line in lines[:30]:
        normalized_line = normalize_description(line)
        if "OUROCARD" in normalized_line:
            metadata.card_name = "Ourocard"
            if metadata.card_brand:
                metadata.card_name = f"Ourocard {metadata.card_brand}"
            break
        if "CARTAO" in normalized_line and metadata.card_brand:
            metadata.card_name = metadata.card_brand

    return metadata


def _caixa_statement_metadata(text: str, fallback_year: int) -> StatementMetadata:
    metadata = _statement_metadata(text, fallback_year)
    metadata.card_institution = "Caixa"
    metadata.card_limit_amount = _extract_caixa_card_limit(text) or metadata.card_limit_amount

    total_match = re.search(
        r"VALOR TOTAL DESTA FATURA\s+(?:R\$\s*)?(?P<amount>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
        text,
        re.IGNORECASE,
    )
    if total_match:
        metadata.statement_total_amount = parse_brazilian_money(total_match.group("amount"))

    due_match = re.search(r"VENCIMENTO\s+(?P<date>\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    if due_match:
        metadata.statement_due_date = _parse_date(due_match.group("date"), fallback_year)

    card_match = re.search(r"(?P<digits>\d{4})\s*$", text.splitlines()[0].strip()) if text.splitlines() else None
    if card_match:
        metadata.card_last_digits = card_match.group("digits")

    if metadata.statement_reference_month is None and metadata.statement_due_date:
        metadata.statement_reference_month = date(metadata.statement_due_date.year, metadata.statement_due_date.month, 1)

    return metadata


def _split_country(body: str) -> tuple[str, str | None]:
    body = re.sub(r"\bR\$\s*$", "", body).strip()
    parts = body.rsplit(" ", 1)
    if len(parts) == 2 and normalize_description(parts[1]) in COUNTRY_CODES:
        return parts[0].strip(), parts[1].strip().upper()
    return body.strip(), None


def _installment(description: str) -> tuple[int | None, int | None]:
    parc_match = re.search(r"\bPARC\s*(?P<current>\d{1,2})\s*/\s*(?P<total>\d{1,2})\b", description, re.IGNORECASE)
    if parc_match:
        return int(parc_match.group("current")), int(parc_match.group("total"))
    return detect_installment(description)


def _extract_invoice_installment(description: str) -> tuple[str, int | None, int | None]:
    match = re.search(r"\(?\bParcela\s+(?P<current>\d{1,2})\s+de\s+(?P<total>\d{1,2})\)?", description, re.IGNORECASE)
    if match:
        cleaned = f"{description[:match.start()]} {description[match.end():]}".strip()
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
        return cleaned, int(match.group("current")), int(match.group("total"))
    installment_current, installment_total = _installment(description)
    return description, installment_current, installment_total


def _transaction_type(description: str) -> tuple[TransactionType, ExcludedReason | None]:
    normalized = normalize_description(description)
    if re.search(r"\b(PGTO|PAGAMENTO)\b", normalized):
        return TransactionType.payment, ExcludedReason.payment
    if re.search(r"\b(CREDITO|ESTORNO|DEVOLUCAO)\b", normalized):
        return TransactionType.refund, ExcludedReason.refund
    return TransactionType.expense, None


def _confidence(section: str | None, country: str | None, installment_total: int | None, tx_type: TransactionType) -> float:
    score = Decimal("0.72")
    if section:
        score += Decimal("0.10")
    if country:
        score += Decimal("0.05")
    if installment_total:
        score += Decimal("0.04")
    if tx_type in {TransactionType.payment, TransactionType.refund}:
        score += Decimal("0.04")
    return float(min(score, Decimal("0.95")))


def _is_caixa_ignored_line(line: str) -> ExcludedReason | None:
    normalized = normalize_description(line)
    if not normalized:
        return ExcludedReason.informativo
    if normalized.startswith("TOTAL COMPRAS") or normalized.startswith("TOTAL FINAL") or normalized.startswith("VALOR TOTAL DESTA FATURA"):
        return ExcludedReason.total
    if "TOTAL DA FATURA ANTERIOR" in normalized:
        return ExcludedReason.saldo_anterior
    if "OBRIGADO PELO PAGAMENTO" in normalized:
        return ExcludedReason.payment
    if any(
        keyword in normalized
        for keyword in (
            "CENTRAL DE ATENDIMENTO",
            "INFORMACOES COMPLEMENTARES",
            "LIMITES",
            "SALDO PREVISTO",
            "DESPESAS A VENCER",
            "DEMONSTRATIVO",
            "GUIA DE CONSUMO",
            "ANUIDADE",
            "ENCARGOS",
            "MULTA",
            "MORA",
            "PARCELAMENTO",
            "CET",
            "ROTATIVO",
            "SAC CAIXA",
            "OUVIDORIA",
            "BOLETO",
            "BENEFICIARIO",
            "PAGADOR",
            "LOCAL DE PAGAMENTO",
        )
    ):
        return ExcludedReason.informativo
    return None


def _parse_caixa_card_statement(text: str) -> ParserResult:
    fallback_year = _statement_year(text)
    metadata = _caixa_statement_metadata(text, fallback_year)
    previews: list[NormalizedTransactionPreview] = []
    ignored_lines: list[IgnoredPdfLine] = []
    current_card_digits = metadata.card_last_digits
    in_purchases = False
    seen_transactions: set[tuple[str, str, str, str | None]] = set()

    for raw_line in text.splitlines():
        line = _clean(raw_line)
        if not line:
            continue

        normalized = normalize_description(line)
        card_match = CAIXA_CARD_BLOCK_RE.search(normalized)
        if card_match:
            current_card_digits = card_match.group("digits")
            in_purchases = "COMPRAS" in normalized
            continue

        if normalized.startswith("COMPRAS"):
            in_purchases = True
            continue

        match = CAIXA_CARD_TRANSACTION_RE.match(line)
        if not match:
            ignored_reason = _is_caixa_ignored_line(line)
            if ignored_reason:
                ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ignored_reason))
                if ignored_reason == ExcludedReason.total:
                    in_purchases = False
                continue
            if DATE_AMOUNT_RE.match(line):
                ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.low_confidence))
            continue

        if not in_purchases:
            ignored_lines.append(
                IgnoredPdfLine(raw_text=line, excluded_reason=_is_caixa_ignored_line(line) or ExcludedReason.informativo)
            )
            continue

        sign = match.group("sign").upper()
        body = match.group("body").strip()
        description, city_or_country = _split_country(body)
        description = normalize_description(description.title())
        if not description:
            ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.low_confidence))
            continue

        amount = abs(parse_brazilian_money(match.group("amount")))
        tx_type = TransactionType.expense if sign == "D" else TransactionType.refund
        excluded_reason = ExcludedReason.refund if tx_type == TransactionType.refund else None
        signature = (match.group("date"), normalize_description(description), str(amount), current_card_digits)
        if signature in seen_transactions:
            ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.duplicate))
            continue
        seen_transactions.add(signature)

        item_metadata = metadata.model_copy()
        if current_card_digits:
            item_metadata.card_last_digits = current_card_digits

        previews.append(
            NormalizedTransactionPreview(
                transaction_date=_parse_date(match.group("date"), fallback_year),
                description=description,
                original_description=body,
                amount=amount,
                type=tx_type,
                merchant_country=city_or_country,
                raw_text=line,
                raw_row={
                    "line": line,
                    "card_last_digits": current_card_digits,
                    "city_or_country": city_or_country,
                    "parser": "caixa_card_statement_line_v1",
                },
                parser_confidence=0.9 if current_card_digits else 0.82,
                needs_review=False,
                default_selected=tx_type == TransactionType.expense,
                excluded_reason=excluded_reason,
                statement_total_amount=item_metadata.statement_total_amount,
                statement_due_date=item_metadata.statement_due_date,
                statement_reference_month=item_metadata.statement_reference_month,
                card_last_digits=item_metadata.card_last_digits,
                card_name=item_metadata.card_name,
                card_brand=item_metadata.card_brand,
                card_institution=item_metadata.card_institution,
                card_limit_amount=item_metadata.card_limit_amount,
            )
        )

    return ParserResult(items=previews, ignored_lines=ignored_lines, statement_metadata=metadata)


def _inter_statement_metadata(text: str, fallback_year: int) -> StatementMetadata:
    metadata = _statement_metadata(text, fallback_year)
    metadata.card_institution = "Banco Inter"
    metadata.card_name = "Inter"
    metadata.card_brand = None

    header_match = re.search(
        r"(?P<digits>\d{4}\*+\d{4})\s+(?P<due>\d{2}/\d{2}/\d{4})\s+R\$\s*(?P<total>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
        text,
        re.IGNORECASE,
    )
    if header_match:
        metadata.card_last_digits = header_match.group("digits")[-4:]
        metadata.statement_due_date = _parse_date(header_match.group("due"), fallback_year)
        metadata.statement_total_amount = parse_brazilian_money(header_match.group("total"))

    limit_total_match = re.search(
        r"Limite de cr.dito total.*?R\$\s*(?P<limit>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if limit_total_match:
        metadata.card_limit_amount = parse_brazilian_money(limit_total_match.group("limit"))

    if metadata.statement_reference_month is None and metadata.statement_due_date:
        metadata.statement_reference_month = date(metadata.statement_due_date.year, metadata.statement_due_date.month, 1)

    return metadata


def _is_inter_ignored_line(line: str) -> ExcludedReason | None:
    normalized = normalize_description(line)
    if not normalized:
        return ExcludedReason.informativo
    if normalized.startswith("TOTAL CARTAO") or normalized.startswith("TOTAL A PAGAR") or normalized.startswith("FATURA ATUAL"):
        return ExcludedReason.total
    if "PAGAMENTO ON LINE" in normalized or "PAGAMENTO DA FATURA" in normalized:
        return ExcludedReason.payment
    if any(
        keyword in normalized
        for keyword in (
            "RESUMO DA FATURA",
            "SUA FATURA CHEGOU",
            "LIMITE DE CREDITO",
            "DATA DE VENCIMENTO",
            "PAGAMENTO MINIMO",
            "ENCARGOS",
            "IOF",
            "ROTATIVO",
            "PAGAMENTO VIA",
            "BOLETO",
            "PIX",
            "PARCELAMENTO",
            "DESCRITIVO DETALHADO",
            "PROXIMA FATURA",
            "FALE COM A GENTE",
            "LOCAL DE PAGAMENTO",
            "BENEFICIARIO",
            "PAGADOR",
            "AUTENTICACAO MECANICA",
        )
    ):
        return ExcludedReason.informativo
    return None


def _parse_inter_card_statement(text: str) -> ParserResult:
    fallback_year = _statement_year(text)
    metadata = _inter_statement_metadata(text, fallback_year)
    previews: list[NormalizedTransactionPreview] = []
    ignored_lines: list[IgnoredPdfLine] = []
    current_card_digits = metadata.card_last_digits
    seen_transactions: set[tuple[str, str, str, str | None]] = set()

    for raw_line in text.splitlines():
        line = _clean(raw_line)
        if not line:
            continue

        card_match = INTER_CARD_BLOCK_RE.search(line)
        if card_match:
            current_card_digits = card_match.group("digits")
            continue

        match = INTER_CARD_TRANSACTION_RE.match(line)
        if not match:
            ignored_reason = _is_inter_ignored_line(line)
            if ignored_reason:
                ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ignored_reason))
            elif DATE_AMOUNT_RE.match(line):
                ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.low_confidence))
            continue

        body = match.group("body").strip()
        normalized_body = normalize_description(body)
        sign = match.group("sign")
        if sign or "PAGAMENTO" in normalized_body:
            ignored_lines.append(
                IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.payment if "PAGAMENTO" in normalized_body else ExcludedReason.refund)
            )
            continue

        description, installment_current, installment_total = _extract_invoice_installment(body)
        description = normalize_description(description)
        if not description:
            ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.low_confidence))
            continue

        amount = abs(parse_brazilian_money(match.group("amount")))
        tx_date = date(int(match.group("year")), SHORT_MONTHS.get(normalize_description(match.group("month")).lower()[:3], 1), int(match.group("day")))
        signature = (tx_date.isoformat(), description, str(amount), current_card_digits)
        if signature in seen_transactions:
            ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.duplicate))
            continue
        seen_transactions.add(signature)

        item_metadata = metadata.model_copy()
        if current_card_digits:
            item_metadata.card_last_digits = current_card_digits

        previews.append(
            NormalizedTransactionPreview(
                transaction_date=tx_date,
                description=description,
                original_description=body,
                amount=amount,
                type=TransactionType.expense,
                installment_current=installment_current,
                installment_total=installment_total,
                raw_text=line,
                raw_row={
                    "line": line,
                    "card_last_digits": current_card_digits,
                    "parser": "inter_card_statement_line_v1",
                },
                parser_confidence=0.9 if current_card_digits else 0.82,
                needs_review=False,
                default_selected=True,
                statement_total_amount=item_metadata.statement_total_amount,
                statement_due_date=item_metadata.statement_due_date,
                statement_reference_month=item_metadata.statement_reference_month,
                card_last_digits=item_metadata.card_last_digits,
                card_name=item_metadata.card_name,
                card_brand=item_metadata.card_brand,
                card_institution=item_metadata.card_institution,
                card_limit_amount=item_metadata.card_limit_amount,
            )
        )

    return ParserResult(items=previews, ignored_lines=ignored_lines, statement_metadata=metadata)


def _mercado_pago_statement_metadata(text: str, fallback_year: int) -> StatementMetadata:
    metadata = _statement_metadata(text, fallback_year)
    metadata.card_institution = "Mercado Pago"
    metadata.card_name = "Mercado Pago Visa"
    metadata.card_brand = "Visa"

    summary_match = re.search(
        r"Total a pagar\s+Vence em\s+Limite total.*?R\$\s*(?P<total>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})\s+"
        r"(?P<due>\d{2}/\d{2}/\d{4})\s+R\$\s*(?P<limit>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if summary_match:
        metadata.statement_total_amount = parse_brazilian_money(summary_match.group("total"))
        metadata.statement_due_date = _parse_date(summary_match.group("due"), fallback_year)
        metadata.card_limit_amount = parse_brazilian_money(summary_match.group("limit"))

    due_match = re.search(r"Vencimento:\s*(?P<due>\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    if due_match:
        metadata.statement_due_date = _parse_date(due_match.group("due"), fallback_year)

    first_card_match = MERCADO_PAGO_CARD_BLOCK_RE.search(text)
    if first_card_match:
        metadata.card_last_digits = first_card_match.group("digits")
        brand = first_card_match.group("brand").upper()
        metadata.card_brand = CARD_BRANDS.get(brand, first_card_match.group("brand").title())
        metadata.card_name = f"Mercado Pago {metadata.card_brand}"

    if metadata.statement_reference_month is None and metadata.statement_due_date:
        metadata.statement_reference_month = date(metadata.statement_due_date.year, metadata.statement_due_date.month, 1)

    return metadata


def _is_mercado_pago_ignored_line(line: str) -> ExcludedReason | None:
    normalized = normalize_description(line)
    if not normalized:
        return ExcludedReason.informativo
    if normalized.startswith("TOTAL"):
        return ExcludedReason.total
    if "PAGAMENTO DA FATURA" in normalized:
        return ExcludedReason.payment
    if any(
        keyword in normalized
        for keyword in (
            "TOTAL A PAGAR",
            "ESSA E SUA FATURA",
            "PARCELAMENTO DE FATURA",
            "PAGAMENTO MINIMO",
            "JUROS",
            "IOF",
            "CET",
            "INFORMACOES COMPLEMENTARES",
            "RESUMO DA FATURA",
            "DETALHES DE CONSUMO",
            "MOVIMENTACOES NA FATURA",
            "SEU CARTAO DE CREDITO",
            "DATAS IMPORTANTES",
            "LIMITE DO CARTAO",
            "SAQUES COM SEU CARTAO",
            "LANCAMENTOS FUTUROS",
            "OPCOES DE PAGAMENTO",
            "COMPRAS INTERNACIONAIS",
            "FALE COM A GENTE",
            "DECLARACAO ANUAL",
        )
    ):
        return ExcludedReason.informativo
    return None


def _parse_mercado_pago_card_statement(text: str) -> ParserResult:
    fallback_year = _statement_year(text)
    metadata = _mercado_pago_statement_metadata(text, fallback_year)
    previews: list[NormalizedTransactionPreview] = []
    ignored_lines: list[IgnoredPdfLine] = []
    current_card_digits = metadata.card_last_digits
    current_card_brand = metadata.card_brand
    in_card_block = False
    seen_transactions: set[tuple[str, str, str, str | None]] = set()

    for raw_line in text.splitlines():
        line = _clean(raw_line)
        if not line:
            continue

        card_match = MERCADO_PAGO_CARD_BLOCK_RE.search(line)
        if card_match:
            current_card_digits = card_match.group("digits")
            brand_key = normalize_description(card_match.group("brand"))
            current_card_brand = CARD_BRANDS.get(brand_key, card_match.group("brand").title())
            in_card_block = True
            continue

        match = MERCADO_PAGO_TRANSACTION_RE.match(line)
        if not match:
            ignored_reason = _is_mercado_pago_ignored_line(line)
            if ignored_reason:
                ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ignored_reason))
            elif DATE_AMOUNT_RE.match(line):
                ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.low_confidence))
            continue

        body = match.group("body").strip()
        normalized_body = normalize_description(body)
        if not in_card_block or "PAGAMENTO DA FATURA" in normalized_body:
            ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.payment))
            continue

        description, installment_current, installment_total = _extract_invoice_installment(body)
        description = normalize_description(description)
        if not description:
            ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.low_confidence))
            continue

        amount = abs(parse_brazilian_money(match.group("amount")))
        tx_date = _parse_date(match.group("date"), fallback_year)
        signature = (tx_date.isoformat(), description, str(amount), current_card_digits)
        if signature in seen_transactions:
            ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.duplicate))
            continue
        seen_transactions.add(signature)

        item_metadata = metadata.model_copy()
        if current_card_digits:
            item_metadata.card_last_digits = current_card_digits
        if current_card_brand:
            item_metadata.card_brand = current_card_brand
            item_metadata.card_name = f"Mercado Pago {current_card_brand}"

        previews.append(
            NormalizedTransactionPreview(
                transaction_date=tx_date,
                description=description,
                original_description=body,
                amount=amount,
                type=TransactionType.expense,
                installment_current=installment_current,
                installment_total=installment_total,
                raw_text=line,
                raw_row={
                    "line": line,
                    "card_last_digits": current_card_digits,
                    "parser": "mercado_pago_card_statement_line_v1",
                },
                parser_confidence=0.9 if current_card_digits else 0.82,
                needs_review=False,
                default_selected=True,
                statement_total_amount=item_metadata.statement_total_amount,
                statement_due_date=item_metadata.statement_due_date,
                statement_reference_month=item_metadata.statement_reference_month,
                card_last_digits=item_metadata.card_last_digits,
                card_name=item_metadata.card_name,
                card_brand=item_metadata.card_brand,
                card_institution=item_metadata.card_institution,
                card_limit_amount=item_metadata.card_limit_amount,
            )
        )

    return ParserResult(items=previews, ignored_lines=ignored_lines, statement_metadata=metadata)


def parse(path: Path, mime_type: str | None = None) -> ParserResult:
    text = _extract_text(path)
    if _is_bank_statement(text):
        return _parse_bank_statement(text)
    if _is_caixa_card_statement(text):
        return _parse_caixa_card_statement(text)
    if _is_inter_card_statement(text):
        return _parse_inter_card_statement(text)
    if _is_mercado_pago_card_statement(text):
        return _parse_mercado_pago_card_statement(text)

    fallback_year = _statement_year(text)
    metadata = _statement_metadata(text, fallback_year)
    previews: list[NormalizedTransactionPreview] = []
    ignored_lines: list[IgnoredPdfLine] = []
    current_section: str | None = None
    seen_transactions: set[tuple[str, str, str, int | None, int | None]] = set()

    for raw_line in text.splitlines():
        line = _clean(raw_line)
        if not line:
            continue

        if _is_section_header(line):
            current_section = _section_for(line)
            continue

        ignored_reason = _ignored_reason(line)
        if ignored_reason:
            ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ignored_reason, section=current_section))
            continue

        match = LINE_RE.match(line)
        if not match:
            if DATE_AMOUNT_RE.match(line):
                ignored_lines.append(
                    IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.low_confidence, section=current_section)
                )
            continue

        description, country = _split_country(match.group("body").strip(" -"))
        if not description:
            ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.low_confidence, section=current_section))
            continue

        amount = abs(parse_brazilian_money(match.group("amount")))
        installment_current, installment_total = _installment(description)
        tx_type, excluded_reason = _transaction_type(description)
        signature = (
            match.group("date"),
            normalize_description(description),
            str(amount),
            installment_current,
            installment_total,
        )
        if signature in seen_transactions:
            ignored_lines.append(IgnoredPdfLine(raw_text=line, excluded_reason=ExcludedReason.duplicate, section=current_section))
            continue
        seen_transactions.add(signature)

        confidence = _confidence(current_section, country, installment_total, tx_type)
        needs_review = confidence < 0.7
        if needs_review:
            excluded_reason = ExcludedReason.low_confidence

        default_selected = tx_type == TransactionType.expense and not needs_review

        previews.append(
            NormalizedTransactionPreview(
                transaction_date=_parse_date(match.group("date"), fallback_year),
                description=description,
                original_description=description,
                amount=amount,
                type=tx_type,
                suggested_category=current_section,
                merchant_country=country,
                installment_current=installment_current,
                installment_total=installment_total,
                raw_text=line,
                raw_row={
                    "line": line,
                    "section": current_section,
                    "country": country,
                    "parser": "pdf_statement_line_v2",
                },
                parser_confidence=confidence,
                needs_review=needs_review,
                default_selected=default_selected,
                excluded_reason=excluded_reason,
                statement_total_amount=metadata.statement_total_amount,
                statement_due_date=metadata.statement_due_date,
                statement_reference_month=metadata.statement_reference_month,
                card_last_digits=metadata.card_last_digits,
                card_name=metadata.card_name,
                card_brand=metadata.card_brand,
                card_institution=metadata.card_institution,
                card_limit_amount=metadata.card_limit_amount,
            )
        )

    return ParserResult(items=previews, ignored_lines=ignored_lines, statement_metadata=metadata)

from decimal import Decimal
from pathlib import Path

from reportlab.pdfgen import canvas

from app.models.enums import ExcludedReason, TransactionType
from app.parsers.pdf_parser import parse


def _make_pdf(path: Path, lines: list[str]) -> None:
    pdf = canvas.Canvas(str(path))
    y = 800
    for line in lines:
        pdf.drawString(40, y, line)
        y -= 18
    pdf.save()


def test_pdf_parser_extracts_banco_do_brasil_like_invoice(tmp_path: Path) -> None:
    path = tmp_path / "bb-fatura-anonimizada.pdf"
    _make_pdf(
        path,
        [
            "Banco do Brasil Ourocard Elo",
            "Cartao final 1234",
            "Limite único R$ 5.000,00",
            "Referencia 05/2026",
            "Vencimento 15/05/2026",
            "Saldo fatura anterior R$ 100,00",
            "Lancamentos nesta fatura",
            "Supermercados",
            "03/05 MERCADO EXEMPLO 001 BRA 55,90",
            "Servicos",
            "04/05 APP TRANSPORTE BRA 22,10",
            "Compras parceladas",
            "05/05 COMPRA PARCELADA PARC 02/06 BRA 120,00",
            "Outros lancamentos",
            "06/05 PGTO FATURA BRA 100,00",
            "07/05 ESTORNO COMPRA BRA 10,00",
            "Subtotal R$ 198,00",
            "Total da fatura R$ 198,00",
        ],
    )

    result = parse(path)
    items = result.items

    assert [item.description for item in items] == [
        "MERCADO EXEMPLO 001",
        "APP TRANSPORTE",
        "COMPRA PARCELADA PARC 02/06",
        "PGTO FATURA",
        "ESTORNO COMPRA",
    ]
    assert items[0].suggested_category == "Supermercados"
    assert items[0].merchant_country == "BRA"
    assert items[2].suggested_category == "Compras parceladas"
    assert items[2].installment_current == 2
    assert items[2].installment_total == 6
    assert items[3].type == TransactionType.payment
    assert items[3].default_selected is False
    assert items[3].excluded_reason == ExcludedReason.payment
    assert items[4].type == TransactionType.refund
    assert items[4].default_selected is False
    assert items[4].excluded_reason == ExcludedReason.refund

    selected_total = sum(item.amount for item in items if item.default_selected)
    assert selected_total == Decimal("198.00")
    assert result.statement_metadata.statement_total_amount == Decimal("198.00")
    assert result.statement_metadata.statement_due_date.isoformat() == "2026-05-15"
    assert result.statement_metadata.statement_reference_month.isoformat() == "2026-05-01"
    assert result.statement_metadata.card_last_digits == "1234"
    assert result.statement_metadata.card_name == "Ourocard Elo"
    assert result.statement_metadata.card_brand == "Elo"
    assert result.statement_metadata.card_institution == "Banco do Brasil"
    assert result.statement_metadata.card_limit_amount == Decimal("5000.00")
    assert items[0].card_last_digits == "1234"
    assert items[0].card_name == "Ourocard Elo"
    assert items[0].card_brand == "Elo"
    assert items[0].card_institution == "Banco do Brasil"
    assert items[0].card_limit_amount == Decimal("5000.00")

    ignored_reasons = [line.excluded_reason for line in result.ignored_lines]
    assert ExcludedReason.saldo_anterior in ignored_reasons
    assert ExcludedReason.subtotal in ignored_reasons
    assert ExcludedReason.total in ignored_reasons


def test_pdf_parser_filters_informative_lines(tmp_path: Path) -> None:
    path = tmp_path / "bb-fatura-informativos.pdf"
    _make_pdf(
        path,
        [
            "Vencimento 15/05/2026",
            "Central de Atendimento 4004 0001",
            "IOF R$ 1,20",
            "Lancamentos nesta fatura",
            "Restaurantes",
            "06/05 RESTAURANTE EXEMPLO BRA 45,30",
            "Total da fatura R$ 45,30",
        ],
    )

    result = parse(path)

    assert len(result.items) == 1
    assert result.items[0].description == "RESTAURANTE EXEMPLO"
    assert result.items[0].suggested_category == "Restaurantes"
    assert ExcludedReason.informativo in [line.excluded_reason for line in result.ignored_lines]


def test_pdf_parser_extracts_banco_do_brasil_checking_statement(tmp_path: Path) -> None:
    path = tmp_path / "bb-extrato-anonimizado.pdf"
    _make_pdf(
        path,
        [
            "Extrato de Conta Corrente",
            "Cliente GABRIEL A F ALMEIDA",
            "Período: 01 a 31/05/2026 Agência: 3970-5 Conta: 29537-X",
            "Lançamentos",
            "Dia Lote Documento Histórico Valor",
            "09/04/2026 Saldo Anterior 639,83 (+)",
            "Pix - Recebido",
            "05/05/2026 14397 51444178435132 05/05 14:44 00034452453805 GABRIEL ARN 100,00 (+)",
            "Pagto cartão crédito",
            "05/05/2026 99020 700397000056149 650,73 (-)",
            "Saldo do dia 89,10 (+)",
            "Transferência recebida",
            "07/05/2026 99020 603970400029537 2.190,34 (+)",
            "07/05 16:17 GABRIEL A F ALMEIDA",
            "Pagamento de Boleto",
            "08/05/2026 13105 50803 542,37 (-)",
            "CARTOES CAIXA ELO PF",
            "31/05/2026 S A L D O 233,26 (+)",
            "Total Aplicações Financeiras 0,00",
        ],
    )

    result = parse(path)

    assert result.statement_metadata.account_institution == "Banco do Brasil"
    assert result.statement_metadata.account_agency == "3970-5"
    assert result.statement_metadata.account_number == "29537-X"
    assert result.statement_metadata.account_balance == Decimal("233.26")
    assert len(result.items) == 4
    assert result.items[0].description.startswith("Pix - Recebido")
    assert result.items[0].amount == Decimal("100.00")
    assert result.items[0].type == TransactionType.income
    assert result.items[1].type == TransactionType.payment
    assert result.items[1].default_selected is False
    assert result.items[2].description.endswith("07/05 16:17 GABRIEL A F ALMEIDA")
    assert result.items[3].description.endswith("CARTOES CAIXA ELO PF")
    assert all(item.account_agency == "3970-5" for item in result.items)

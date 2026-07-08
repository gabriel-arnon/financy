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


def test_pdf_parser_extracts_caixa_card_statement(tmp_path: Path) -> None:
    path = tmp_path / "caixa-fatura-anonimizada.pdf"
    _make_pdf(
        path,
        [
            "Central de Atendimento Cartoes Caixa",
            "6505.XXXX.XXXX.6823",
            "VENCIMENTO",
            "17/06/2026",
            "VALOR TOTAL DESTA FATURA",
            "R$ 492,59",
            "Limites Melhor data para compra: 08/07/2026",
            "TOTAL R$ 950,00",
            "UTILIZADO R$ 492,59",
            "DISPONIVEL R$ 457,41",
            "Guia de Consumo 07/05 TOTAL DA FATURA ANTERIOR 542,37D",
            "08/05 OBRIGADO PELO PAGAMENTO 542,37C",
            "GABRIEL A F ALMEIDA (Cartao 6823)",
            "COMPRAS (Cartao 6823)",
            "08/05 REST CARAVELAS BERTIOGA 12,67D",
            "09/05 MP MERCADAKAMPAI OSASCO 10,49D",
            "MULTA 2,00% 26/05 FLORICULTURA TAQUARI SAO PAULO 15,00D",
            "Total COMPRAS 38,16D",
            "GABRIEL A F ALMEIDA (Cartao 7164)",
            "COMPRAS (Cartao 7164)",
            "16/05 99Food Top Cookie Moo Sao Paulo 21,30D",
            "16/05 99APP 99App Sao Paulo 31,50D",
            "Total COMPRAS 52,80D",
            "Valor total desta fatura R$ 492,59 D",
        ],
    )

    result = parse(path)
    items = result.items

    assert [item.description for item in items] == [
        "REST CARAVELAS BERTIOGA",
        "MP MERCADAKAMPAI OSASCO",
        "FLORICULTURA TAQUARI SAO PAULO",
        "99FOOD TOP COOKIE MOO SAO PAULO",
        "99APP 99APP SAO PAULO",
    ]
    assert [item.card_last_digits for item in items] == ["6823", "6823", "6823", "7164", "7164"]
    assert all(item.type == TransactionType.expense for item in items)
    assert all(item.default_selected for item in items)
    assert sum(item.amount for item in items) == Decimal("90.96")
    assert result.statement_metadata.statement_total_amount == Decimal("492.59")
    assert result.statement_metadata.statement_due_date.isoformat() == "2026-06-17"
    assert result.statement_metadata.statement_reference_month.isoformat() == "2026-06-01"
    assert result.statement_metadata.card_last_digits == "6823"
    assert result.statement_metadata.card_institution == "Caixa"
    assert result.statement_metadata.card_limit_amount == Decimal("950.00")
    assert items[0].raw_row["parser"] == "caixa_card_statement_line_v1"
    ignored_reasons = [line.excluded_reason for line in result.ignored_lines]
    assert ExcludedReason.saldo_anterior in ignored_reasons
    assert ExcludedReason.payment in ignored_reasons
    assert ExcludedReason.total in ignored_reasons


def test_pdf_parser_extracts_inter_card_statement(tmp_path: Path) -> None:
    path = tmp_path / "inter-fatura-anonimizada.pdf"
    _make_pdf(
        path,
        [
            "Banco Inter",
            "Resumo da fatura",
            "Limite de credito total Total da sua fatura",
            "R$ 3.500,00",
            "R$ 637,14",
            "2306****8928 12/06/2026 R$ 637,14",
            "Despesas da fatura",
            "CARTAO 2306****8928",
            "Data Movimentacao Beneficiario Valor",
            "24 de dez. 2025 HNA*OBOTICARIO (Parcela 06 de 06) - R$ 82,17",
            "08 de mai. 2026 PAGAMENTO ON LINE - + R$ 735,61",
            "16 de mai. 2026 MP *BRUNOJOSESILV - R$ 50,00",
            "Total CARTAO 2306****8928 R$ 132,17",
            "CARTAO 2306****1140",
            "21 de mar. 2026 ZP *OLX GABRIEL RIBEIR (Parcela 03 de 03) - R$ 126,16",
            "10 de mai. 2026 SEGURO CARTAO CTP - R$ 5,90",
            "14 de mai. 2026 ADEMICON IMOVEIS - R$ 348,06",
            "18 de mai. 2026 IFD*IFOOD CLUB - R$ 4,95",
            "18 de mai. 2026 Google Crunchyroll An - R$ 19,90",
            "Total CARTAO 2306****1140 R$ 504,97",
        ],
    )

    result = parse(path)
    items = result.items

    assert [item.description for item in items] == [
        "HNA*OBOTICARIO",
        "MP *BRUNOJOSESILV",
        "ZP *OLX GABRIEL RIBEIR",
        "SEGURO CARTAO CTP",
        "ADEMICON IMOVEIS",
        "IFD*IFOOD CLUB",
        "GOOGLE CRUNCHYROLL AN",
    ]
    assert [item.card_last_digits for item in items] == ["8928", "8928", "1140", "1140", "1140", "1140", "1140"]
    assert all(item.type == TransactionType.expense for item in items)
    assert all(item.default_selected for item in items)
    assert sum(item.amount for item in items) == Decimal("637.14")
    assert items[0].installment_current == 6
    assert items[0].installment_total == 6
    assert result.statement_metadata.statement_total_amount == Decimal("637.14")
    assert result.statement_metadata.statement_due_date.isoformat() == "2026-06-12"
    assert result.statement_metadata.statement_reference_month.isoformat() == "2026-06-01"
    assert result.statement_metadata.card_limit_amount == Decimal("3500.00")
    assert result.statement_metadata.card_institution == "Banco Inter"
    assert items[0].raw_row["parser"] == "inter_card_statement_line_v1"
    ignored_reasons = [line.excluded_reason for line in result.ignored_lines]
    assert ExcludedReason.payment in ignored_reasons
    assert ExcludedReason.total in ignored_reasons


def test_pdf_parser_extracts_mercado_pago_card_statement(tmp_path: Path) -> None:
    path = tmp_path / "mercado-pago-fatura-anonimizada.pdf"
    _make_pdf(
        path,
        [
            "Mercado Pago",
            "Emitida em: 06/07/2026",
            "Essa e sua fatura de julho",
            "Total a pagar Vence em Limite total Saque total",
            "R$ 351,96 10/07/2026 R$ 2.400,00 R$ 50,00",
            "Detalhes de consumo",
            "Movimentacoes na fatura",
            "Data Movimentacoes Valor em R$",
            "08/06 Pagamento da fatura de junho/2026 R$ 554,80",
            "Cartao Visa [************2812]",
            "Data Movimentacoes Valor em R$",
            "13/04 MERCADOLIVRE*MERCADOLIVRE Parcela 3 de 5 R$ 11,31",
            "13/05 PORTO SEGURO CIA SEG G Parcela 2 de 10 R$ 120,65",
            "Total R$ 131,96",
            "Cartao Visa [************2008]",
            "14/06 REDE CONFIANCA R$ 200,00",
            "04/07 AUTO POSTO BETMAR R$ 20,00",
            "Total R$ 220,00",
        ],
    )

    result = parse(path)
    items = result.items

    assert [item.description for item in items] == [
        "MERCADOLIVRE*MERCADOLIVRE",
        "PORTO SEGURO CIA SEG G",
        "REDE CONFIANCA",
        "AUTO POSTO BETMAR",
    ]
    assert [item.card_last_digits for item in items] == ["2812", "2812", "2008", "2008"]
    assert all(item.type == TransactionType.expense for item in items)
    assert all(item.default_selected for item in items)
    assert sum(item.amount for item in items) == Decimal("351.96")
    assert items[0].installment_current == 3
    assert items[0].installment_total == 5
    assert result.statement_metadata.statement_total_amount == Decimal("351.96")
    assert result.statement_metadata.statement_due_date.isoformat() == "2026-07-10"
    assert result.statement_metadata.statement_reference_month.isoformat() == "2026-07-01"
    assert result.statement_metadata.card_limit_amount == Decimal("2400.00")
    assert result.statement_metadata.card_institution == "Mercado Pago"
    assert result.statement_metadata.card_brand == "Visa"
    assert items[0].raw_row["parser"] == "mercado_pago_card_statement_line_v1"
    ignored_reasons = [line.excluded_reason for line in result.ignored_lines]
    assert ExcludedReason.payment in ignored_reasons
    assert ExcludedReason.total in ignored_reasons

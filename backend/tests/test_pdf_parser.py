from pathlib import Path

from reportlab.pdfgen import canvas

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
            "Banco do Brasil Ourocard",
            "Vencimento 15/05/2026",
            "Saldo anterior R$ 100,00",
            "03/05 MERCADO EXEMPLO 001 55,90",
            "04/05 APP TRANSPORTE 22,10",
            "05/05 COMPRA PARCELADA 02/06 120,00",
            "Pagamento da fatura R$ 100,00",
            "Subtotal R$ 198,00",
            "Total da fatura R$ 198,00",
        ],
    )

    items = parse(path)

    assert [item.description for item in items] == [
        "MERCADO EXEMPLO 001",
        "APP TRANSPORTE",
        "COMPRA PARCELADA 02/06",
    ]
    assert items[2].installment_current == 2
    assert items[2].installment_total == 6


def test_pdf_parser_filters_informative_lines(tmp_path: Path) -> None:
    path = tmp_path / "bb-fatura-informativos.pdf"
    _make_pdf(
        path,
        [
            "Vencimento 15/05/2026",
            "Central de Atendimento 4004 0001",
            "IOF R$ 1,20",
            "06/05 FARMACIA EXEMPLO 45,30",
            "Total da fatura R$ 46,50",
        ],
    )

    items = parse(path)

    assert len(items) == 1
    assert items[0].description == "FARMACIA EXEMPLO"

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.parsers.pdf_parser import parse  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa o parser PDF sem salvar nada no banco.")
    parser.add_argument("pdf_path", help="Caminho local do PDF da fatura")
    args = parser.parse_args()

    path = Path(args.pdf_path)
    if not path.exists():
        print(f"Arquivo nao encontrado: {path}", file=sys.stderr)
        return 1

    result = parse(path)
    selected_total = sum((item.amount for item in result.items if item.default_selected), Decimal("0"))

    print("== Metadados da fatura ==")
    print(result.statement_metadata.model_dump_json(indent=2))

    print("\n== Transacoes extraidas ==")
    for index, item in enumerate(result.items, start=1):
        installment = ""
        if item.installment_current and item.installment_total:
            installment = f" parc {item.installment_current}/{item.installment_total}"
        print(
            f"{index:03d} | {item.transaction_date} | {item.type} | "
            f"default_selected={item.default_selected} | conf={item.parser_confidence:.2f} | "
            f"{item.suggested_category or '-'} | {item.merchant_country or '-'} | "
            f"{item.description}{installment} | {item.amount} | reason={item.excluded_reason or '-'}"
        )

    print("\n== Linhas ignoradas ==")
    for line in result.ignored_lines:
        print(f"{line.excluded_reason} | {line.section or '-'} | {line.raw_text}")

    print("\n== Soma selecionavel ==")
    print(selected_total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

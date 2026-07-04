from pathlib import Path

import pytest

from app.core.errors import AppError
from app.parsers.parser_factory import ParserFactory


def test_parser_factory_rejects_unsupported_file(tmp_path: Path) -> None:
    path = tmp_path / "statement.txt"
    path.write_text("x", encoding="utf-8")

    with pytest.raises(AppError):
        ParserFactory.parse(path=path, filename="statement.txt", mime_type="text/plain")


def test_parser_factory_accepts_csv_by_extension(tmp_path: Path) -> None:
    path = tmp_path / "statement.csv"
    path.write_text("data,descricao,valor\n01/05/2026,Cafe,\"12,50\"\n", encoding="utf-8")

    result = ParserFactory.parse(path=path, filename="statement.csv", mime_type=None)

    assert len(result.items) == 1
    assert result.items[0].description == "Cafe"
    assert result.ignored_lines == []


def test_parser_factory_accepts_csv_with_dot_decimal_amount(tmp_path: Path) -> None:
    path = tmp_path / "statement.csv"
    path.write_text("date,description,amount\n2026-07-01,Salary,2500.00\n", encoding="utf-8")

    result = ParserFactory.parse(path=path, filename="statement.csv", mime_type="text/csv")

    assert len(result.items) == 1
    assert result.items[0].amount == 2500

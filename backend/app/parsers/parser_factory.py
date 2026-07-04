from pathlib import Path

from app.core.errors import AppError
from app.schemas.common import ParserResult
from app.parsers import csv_parser, ofx_parser, pdf_parser, xlsx_parser


SUPPORTED_EXTENSIONS = {
    ".pdf": pdf_parser.parse,
    ".ofx": ofx_parser.parse,
    ".csv": csv_parser.parse,
    ".xlsx": xlsx_parser.parse,
}

SUPPORTED_MIME_TYPES = {
    "application/pdf": pdf_parser.parse,
    "application/x-ofx": ofx_parser.parse,
    "text/csv": csv_parser.parse,
    "application/vnd.ms-excel": csv_parser.parse,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": xlsx_parser.parse,
}


class ParserFactory:
    @staticmethod
    def parse(path: Path, filename: str, mime_type: str | None) -> ParserResult:
        extension = Path(filename).suffix.lower()
        parser = SUPPORTED_MIME_TYPES.get(mime_type or "") or SUPPORTED_EXTENSIONS.get(extension)
        if parser is None:
            raise AppError("Formato de arquivo nao suportado.", status_code=415, code="unsupported_file_type")
        return parser(path, mime_type)

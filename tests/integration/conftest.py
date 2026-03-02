from __future__ import annotations

import io
from pathlib import Path

import openpyxl
import pytest

from pk_timetable.config import load_config, Config

_RESOURCES = Path(__file__).parent.parent / "resources"
_CONFIG_PATH = Path("config.yaml")

# Accept either format; .xls is converted transparently to xlsx bytes.
_CANDIDATES = [
    _RESOURCES / "test_calendar.xlsx",
    _RESOURCES / "test_calendar.xls",
]


def _xls_to_xlsx_bytes(raw: bytes) -> bytes:
    """Convert legacy .xls bytes to .xlsx bytes via xlrd + openpyxl.

    xlrd reads the binary OLE format; dates/times come back as xldate floats
    which are converted to datetime objects so that parser._to_date / _to_time
    work correctly.
    """
    import xlrd

    book = xlrd.open_workbook(file_contents=raw)
    sheet = book.sheet_by_index(0)

    wb = openpyxl.Workbook()
    ws = wb.active
    for row_idx in range(sheet.nrows):
        row: list = []
        for col_idx in range(sheet.ncols):
            cell = sheet.cell(row_idx, col_idx)
            if cell.ctype == xlrd.XL_CELL_DATE:
                row.append(xlrd.xldate_as_datetime(cell.value, book.datemode))
            else:
                row.append(cell.value)
        ws.append(row)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture(scope="session")
def integration_config() -> Config:
    if not _CONFIG_PATH.exists():
        pytest.skip(f"config.yaml not found — place it at {_CONFIG_PATH.resolve()}")
    return load_config(_CONFIG_PATH)


@pytest.fixture(scope="session")
def timetable_bytes() -> bytes:
    for path in _CANDIDATES:
        if path.exists():
            raw = path.read_bytes()
            if path.suffix == ".xls":
                return _xls_to_xlsx_bytes(raw)
            return raw
    paths = ", ".join(str(p) for p in _CANDIDATES)
    pytest.skip(f"No test timetable found — place one at: {paths}")

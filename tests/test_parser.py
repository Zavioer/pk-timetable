from __future__ import annotations

import io
from datetime import date, time

import openpyxl
import pytest

from pk_timetable.config import ColumnMap
from pk_timetable.parser import parse


def _make_xlsx(rows: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


_COL_MAP = ColumnMap(
    header_row=0,
    date=0,
    start_time=1,
    end_time=2,
    subject=3,
    room=4,
    lecturer=5,
    groups=6,
)

_HEADER = ["date", "start", "end", "subject", "room", "lecturer", "groups"]


def test_parse_single_entry() -> None:
    d = date(2025, 3, 10)
    start = time(8, 0)
    end = time(9, 30)
    data = _make_xlsx([_HEADER, [d, start, end, "Matematyka", "A101", "Dr Kowalski", "GR1"]])
    entries = parse(data, _COL_MAP)
    assert len(entries) == 1
    e = entries[0]
    assert e.date == d
    assert e.start_time == start
    assert e.end_time == end
    assert e.subject == "Matematyka"
    assert e.room == "A101"
    assert e.lecturer == "Dr Kowalski"
    assert e.groups == "GR1"


def test_parse_skips_empty_rows() -> None:
    d = date(2025, 3, 10)
    data = _make_xlsx([
        _HEADER,
        [None, None, None, None, None, None, None],
        [d, time(8, 0), time(9, 30), "Fizyka", "B202", "Prof. Nowak", "GR2"],
    ])
    entries = parse(data, _COL_MAP)
    assert len(entries) == 1
    assert entries[0].subject == "Fizyka"


def test_parse_skips_rows_missing_required_fields() -> None:
    d = date(2025, 3, 10)
    data = _make_xlsx([
        _HEADER,
        [d, time(8, 0), None, "Chemia", "C303", "", ""],  # missing end_time
        [d, time(10, 0), time(11, 30), "Biologia", "D404", "", ""],
    ])
    entries = parse(data, _COL_MAP)
    assert len(entries) == 1
    assert entries[0].subject == "Biologia"


def test_parse_empty_sheet() -> None:
    data = _make_xlsx([_HEADER])
    entries = parse(data, _COL_MAP)
    assert entries == []

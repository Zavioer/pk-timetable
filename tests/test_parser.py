from __future__ import annotations

import io
from datetime import date, time

import openpyxl
import pytest

from pk_timetable.config import LayoutConfig
from pk_timetable.parser import parse, _parse_time_range


# ---------------------------------------------------------------------------
# Default layout matching config.yaml defaults
# ---------------------------------------------------------------------------
_LAYOUT = LayoutConfig(
    first_block_row=7,
    block_height=13,
    time_slot_height=3,
    date_col="Q",
    time_col="R",
    group_col="T",
)

_DATE = date(2026, 1, 3)
_GROUP = "CY1"


def _make_grid_xlsx(
    blocks: list[tuple[date, list[tuple[str, str | None]]]],
    first_block_row: int = 7,
    block_height: int = 13,
    time_slot_height: int = 3,
    date_col: str = "Q",
    time_col: str = "R",
    group_col: str = "T",
) -> bytes:
    """Build a minimal grid-layout xlsx for testing.

    Each entry in *blocks* is (date, [(time_range, subject_or_None), ...]).
    Columns before Q are left empty; only Q, R, T are filled.
    """
    from openpyxl.utils import column_index_from_string

    wb = openpyxl.Workbook()
    ws = wb.active

    q = column_index_from_string(date_col)
    r = column_index_from_string(time_col)
    t = column_index_from_string(group_col)

    for block_idx, (block_date, slots) in enumerate(blocks):
        header_row = first_block_row + block_idx * block_height
        data_row = header_row + 1

        # Header row: group name in group_col
        ws.cell(row=header_row, column=t, value=_GROUP)

        # Date in Q (first data row — simulates merged cell)
        ws.cell(row=data_row, column=q, value=block_date)

        for slot_idx, (time_str, subject) in enumerate(slots):
            slot_row = data_row + slot_idx * time_slot_height
            ws.cell(row=slot_row, column=r, value=time_str)
            if subject is not None:
                ws.cell(row=slot_row, column=t, value=subject)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# _parse_time_range unit tests
# ---------------------------------------------------------------------------

def test_parse_time_range_dot_separator() -> None:
    result = _parse_time_range("8.00-10.30")
    assert result == (time(8, 0), time(10, 30))


def test_parse_time_range_colon_separator() -> None:
    result = _parse_time_range("8:00-10:30")
    assert result == (time(8, 0), time(10, 30))


def test_parse_time_range_with_whitespace() -> None:
    result = _parse_time_range(" 10.45 - 12.15 ")
    assert result == (time(10, 45), time(12, 15))


def test_parse_time_range_invalid_returns_none() -> None:
    assert _parse_time_range("not-a-time") is None
    assert _parse_time_range("8.00") is None


# ---------------------------------------------------------------------------
# parse() grid tests
# ---------------------------------------------------------------------------

def test_parse_single_day_one_slot() -> None:
    data = _make_grid_xlsx([(_DATE, [("8.00-10.30", "Matematyka"), (None, None), (None, None), (None, None)])])
    entries = parse(data, _LAYOUT)
    assert len(entries) == 1
    e = entries[0]
    assert e.date == _DATE
    assert e.start_time == time(8, 0)
    assert e.end_time == time(10, 30)
    assert e.subject == "Matematyka"
    assert e.groups == _GROUP


def test_parse_single_day_multiple_slots() -> None:
    slots = [
        ("8.00-10.30", "Matematyka"),
        ("10.45-12.15", "Fizyka"),
        ("12.30-14.00", None),        # no lecture in this slot
        ("14.15-15.45", "Chemia"),
    ]
    data = _make_grid_xlsx([(_DATE, slots)])
    entries = parse(data, _LAYOUT)
    assert len(entries) == 3
    subjects = [e.subject for e in entries]
    assert "Matematyka" in subjects
    assert "Fizyka" in subjects
    assert "Chemia" in subjects


def test_parse_multiple_day_blocks() -> None:
    d1 = date(2026, 1, 3)
    d2 = date(2026, 1, 4)
    data = _make_grid_xlsx([
        (d1, [("8.00-10.30", "Matematyka"), (None, None), (None, None), (None, None)]),
        (d2, [("8.00-10.30", "Fizyka"),     (None, None), (None, None), (None, None)]),
    ])
    entries = parse(data, _LAYOUT)
    assert len(entries) == 2
    assert entries[0].date == d1
    assert entries[1].date == d2


def test_parse_empty_block_stops_iteration() -> None:
    """A block with no date cell signals end of data; nothing after it is parsed."""
    d1 = date(2026, 1, 3)
    data = _make_grid_xlsx([
        (d1, [("8.00-10.30", "Matematyka"), (None, None), (None, None), (None, None)]),
    ])
    entries = parse(data, _LAYOUT)
    assert len(entries) == 1


def test_parse_all_empty_slots_yields_no_entries() -> None:
    data = _make_grid_xlsx([(_DATE, [(None, None), (None, None), (None, None), (None, None)])])
    # date is written but time/subject are absent — no entries expected
    # However the date IS written, so the block is detected.
    # All slots are empty → 0 entries from this block.
    entries = parse(data, _LAYOUT)
    assert entries == []


def test_parse_room_and_lecturer_are_empty() -> None:
    data = _make_grid_xlsx([(_DATE, [("8.00-10.30", "Matematyka"), (None, None), (None, None), (None, None)])])
    e = parse(data, _LAYOUT)[0]
    assert e.room == ""
    assert e.lecturer == ""


def test_parse_groups_comes_from_header_row() -> None:
    data = _make_grid_xlsx([(_DATE, [("8.00-10.30", "Matematyka"), (None, None), (None, None), (None, None)])])
    e = parse(data, _LAYOUT)[0]
    assert e.groups == _GROUP

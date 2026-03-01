from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from datetime import date, time
from typing import Any

import openpyxl

from pk_timetable.config import ColumnMap

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimetableEntry:
    date: date
    start_time: time
    end_time: time
    subject: str
    room: str
    lecturer: str
    groups: str


def _col_index(ws: openpyxl.worksheet.worksheet.Worksheet, col: int | str, header_row: int) -> int:
    """Resolve a column spec (int index or header name) to a 0-based column index."""
    if isinstance(col, int):
        return col
    # Search header row for the matching cell value
    row_values = [cell.value for cell in ws[header_row + 1]]  # openpyxl rows are 1-indexed
    for i, val in enumerate(row_values):
        if val is not None and str(val).strip() == col:
            return i
    raise ValueError(f"Column header {col!r} not found in row {header_row}")


def _to_date(value: Any) -> date | None:
    from datetime import datetime as _datetime
    if isinstance(value, _datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "date") and callable(value.date):
        return value.date()
    return None


def _to_time(value: Any) -> time | None:
    if isinstance(value, time):
        return value
    if hasattr(value, "time"):
        return value.time()
    return None


def parse(data: bytes, col_map: ColumnMap) -> list[TimetableEntry]:
    """Parse xlsx *data* into a list of TimetableEntry objects."""
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    ws = wb.active

    col_map_dict = col_map.model_dump()
    header_row = col_map.header_row

    # Resolve column indices once
    def idx(field: str) -> int | None:
        val = col_map_dict.get(field)
        if val is None:
            return None
        return _col_index(ws, val, header_row)

    date_idx = idx("date")
    start_idx = idx("start_time")
    end_idx = idx("end_time")
    subject_idx = idx("subject")
    room_idx = idx("room")
    lecturer_idx = idx("lecturer")
    groups_idx = idx("groups")

    entries: list[TimetableEntry] = []
    # Data starts after the header row (openpyxl: header_row + 1 is 1-indexed, so data starts at header_row + 2)
    for row in ws.iter_rows(min_row=header_row + 2, values_only=True):
        if all(v is None for v in row):
            continue

        entry_date = _to_date(row[date_idx]) if date_idx is not None else None
        start = _to_time(row[start_idx]) if start_idx is not None else None
        end = _to_time(row[end_idx]) if end_idx is not None else None
        subject = str(row[subject_idx]).strip() if subject_idx is not None and row[subject_idx] is not None else ""

        if entry_date is None or start is None or end is None or not subject:
            logger.debug("Skipping incomplete row: %s", row)
            continue

        room = str(row[room_idx]).strip() if room_idx is not None and row[room_idx] is not None else ""
        lecturer = str(row[lecturer_idx]).strip() if lecturer_idx is not None and row[lecturer_idx] is not None else ""
        groups = str(row[groups_idx]).strip() if groups_idx is not None and row[groups_idx] is not None else ""

        entries.append(TimetableEntry(
            date=entry_date,
            start_time=start,
            end_time=end,
            subject=subject,
            room=room,
            lecturer=lecturer,
            groups=groups,
        ))

    logger.info("Parsed %d entries from timetable", len(entries))
    return entries

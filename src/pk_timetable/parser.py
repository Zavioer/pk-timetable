from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from datetime import date, time
from typing import Any

import openpyxl
from openpyxl.utils import column_index_from_string

from pk_timetable.config import LayoutConfig

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


def _col_to_idx(col: str | int) -> int:
    """Convert an Excel column letter ("Q") or 1-indexed int to a 1-indexed column number
    suitable for openpyxl's ws.cell(row, column)."""
    if isinstance(col, int):
        return col  # already 1-indexed
    return column_index_from_string(col.upper())


def _to_date(value: Any) -> date | None:
    from datetime import datetime as _datetime
    if isinstance(value, _datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "date") and callable(value.date):
        return value.date()
    if isinstance(value, str):
        value = value.strip()
        for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):
            try:
                return _datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _parse_time_range(s: str) -> tuple[time, time] | None:
    """Parse "8.00-10.30" → (time(8, 0), time(10, 30)).

    The separator between start and end is a hyphen; hours and minutes are
    separated by a dot (Polish convention).
    """
    s = s.strip()
    if "-" not in s:
        return None
    parts = s.split("-", 1)
    if len(parts) != 2:
        return None

    def _parse_one(t: str) -> time | None:
        t = t.strip()
        if "." in t:
            h, m = t.split(".", 1)
        elif ":" in t:
            h, m = t.split(":", 1)
        else:
            return None
        try:
            return time(int(h), int(m))
        except (ValueError, TypeError):
            return None

    start = _parse_one(parts[0])
    end = _parse_one(parts[1])
    if start is None or end is None:
        return None
    return start, end


def parse(data: bytes, layout: LayoutConfig) -> list[TimetableEntry]:
    """Parse grid-layout xlsx *data* into a list of TimetableEntry objects.

    The timetable is organised as vertically stacked day blocks.  Each block is
    ``layout.block_height`` rows tall:

    * Row 0 of block (header): group names in the group columns; day name in
      the time column; date column is empty.
    * Rows 1..block_height-1 (data): date column holds the date (merged); time
      column holds "HH.MM-HH.MM" time ranges, one per time slot (each slot
      spans ``layout.time_slot_height`` rows); group column holds the subject
      name (merged when a lecture exists, empty otherwise).
    """
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    ws = wb.active

    date_col = _col_to_idx(layout.date_col)
    time_col = _col_to_idx(layout.time_col)
    group_col = _col_to_idx(layout.group_col)
    num_slots = (layout.block_height - 1) // layout.time_slot_height

    entries: list[TimetableEntry] = []
    block_start = layout.first_block_row  # 1-indexed

    while True:
        # Termination: date cell is in the first data row (block_start + 1)
        date_row = block_start + 1
        if date_row > (ws.max_row or 0):
            break

        date_val = ws.cell(row=date_row, column=date_col).value
        if date_val is None:
            break

        entry_date = _to_date(date_val)
        if entry_date is None:
            logger.debug("Skipping block at row %d: could not parse date %r", block_start, date_val)
            block_start += layout.block_height
            continue

        # Group name comes from the header row of the block
        group_name = ws.cell(row=block_start, column=group_col).value
        group_name = str(group_name).strip() if group_name is not None else ""

        for slot in range(num_slots):
            slot_row = date_row + slot * layout.time_slot_height

            time_val = ws.cell(row=slot_row, column=time_col).value
            subject_val = ws.cell(row=slot_row, column=group_col).value

            if not time_val or not subject_val:
                continue

            times = _parse_time_range(str(time_val))
            if times is None:
                logger.debug("Could not parse time range %r at row %d", time_val, slot_row)
                continue

            start_time, end_time = times
            entries.append(TimetableEntry(
                date=entry_date,
                start_time=start_time,
                end_time=end_time,
                subject=str(subject_val).strip(),
                room="",
                lecturer="",
                groups=group_name,
            ))

        block_start += layout.block_height

    logger.info("Parsed %d entries from timetable", len(entries))
    return entries

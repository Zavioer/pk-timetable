"""Integration tests: parse tests/resources/test_calendar.xls and verify entries."""
from __future__ import annotations

import csv
import logging
from pathlib import Path

import pytest

from pk_timetable.config import Config
from pk_timetable.parser import parse

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration

_OUTPUT_DIR = Path(__file__).parent.parent / "output"
_CSV_PATH = _OUTPUT_DIR / "parsed_entries.csv"


def test_real_timetable_parses_entries(timetable_bytes: bytes, integration_config: Config) -> None:
    entries = parse(timetable_bytes, integration_config.layout)
    logger.info("Parsed %d entries from test_calendar.xls", len(entries))
    for e in entries:
        logger.info("  %s  %s–%s  %s  groups=%s", e.date, e.start_time, e.end_time, e.subject, e.groups)
    assert len(entries) > 0, "Expected at least one entry in the sample timetable"


def test_real_timetable_entry_fields(timetable_bytes: bytes, integration_config: Config) -> None:
    entries = parse(timetable_bytes, integration_config.layout)
    for e in entries:
        assert e.date is not None, f"Entry has no date: {e}"
        assert e.start_time is not None, f"Entry has no start_time: {e}"
        assert e.end_time is not None, f"Entry has no end_time: {e}"
        assert e.subject, f"Entry has empty subject: {e}"
        assert e.start_time < e.end_time, (
            f"start_time {e.start_time} >= end_time {e.end_time} for entry: {e}"
        )


def test_write_parsed_entries_csv(timetable_bytes: bytes, integration_config: Config) -> None:
    """Write all parsed entries to tests/output/parsed_entries.csv (gitignored artifact)."""
    entries = parse(timetable_bytes, integration_config.layout)
    assert len(entries) > 0, "No entries to write — check test_calendar.xls and config.yaml"

    _OUTPUT_DIR.mkdir(exist_ok=True)
    with _CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["group", "date", "start_time", "end_time", "subject"])
        for e in entries:
            writer.writerow([
                e.groups,
                e.date.isoformat(),
                e.start_time.strftime("%H:%M"),
                e.end_time.strftime("%H:%M"),
                e.subject,
            ])

    logger.info("Wrote %d entries to %s", len(entries), _CSV_PATH)
    assert _CSV_PATH.exists()
    assert _CSV_PATH.stat().st_size > 0

"""Integration tests: convert parsed entries to Google Calendar event bodies and verify structure.

No Google Calendar API calls are made — this only exercises the parsing and event-formatting
logic against the real sample timetable file.
"""
from __future__ import annotations

import logging

import pytest

from pk_timetable.config import Config
from pk_timetable.gcal import _entry_to_event
from pk_timetable.parser import parse
from pk_timetable.sync import entry_id, compute_diff

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration


def test_event_bodies_are_well_formed(timetable_bytes: bytes, integration_config: Config) -> None:
    """Each entry must produce a valid Google Calendar event body."""
    entries = parse(timetable_bytes, integration_config.layout)
    assert entries, "No entries parsed — check test_calendar.xlsx and config.yaml columns"

    for e in entries:
        eid = entry_id(e)
        event = _entry_to_event(e, eid, integration_config.timezone)

        logger.info(
            "entry_id=%s  summary=%r  start=%s  end=%s",
            eid, event["summary"],
            event["start"]["dateTime"], event["end"]["dateTime"],
        )

        from pk_timetable.gcal import _build_description
        assert event["summary"] == e.subject
        assert event["location"] == e.room
        assert event["description"] == _build_description(e)
        assert event["start"]["dateTime"]
        assert event["end"]["dateTime"]
        assert event["extendedProperties"]["private"]["source"] == "pk-timetable"
        assert event["extendedProperties"]["private"]["entry_id"] == eid
        assert event["start"]["dateTime"] < event["end"]["dateTime"], (
            f"Event start >= end for entry: {e}"
        )


def test_entry_ids_are_unique(timetable_bytes: bytes, integration_config: Config) -> None:
    """No two entries may share the same stable identity hash."""
    entries = parse(timetable_bytes, integration_config.layout)
    ids = [entry_id(e) for e in entries]
    assert len(ids) == len(set(ids)), (
        f"Duplicate entry_ids found: "
        f"{[eid for eid in ids if ids.count(eid) > 1]}"
    )


def test_compute_diff_against_empty_calendar(timetable_bytes: bytes, integration_config: Config) -> None:
    """Diffing against an empty calendar must schedule all entries for creation."""
    entries = parse(timetable_bytes, integration_config.layout)
    plan = compute_diff(entries, existing_events=[])

    logger.info(
        "Sync plan vs empty calendar: create=%d  update=%d  delete=%d",
        len(plan.to_create), len(plan.to_update), len(plan.to_delete),
    )
    for e in plan.to_create:
        logger.info("  would create: %s on %s %s–%s", e.subject, e.date, e.start_time, e.end_time)

    assert len(plan.to_create) == len(entries)
    assert plan.to_update == []
    assert plan.to_delete == []

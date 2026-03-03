from __future__ import annotations

from datetime import date, time

import pytest

from pk_timetable.parser import TimetableEntry
from pk_timetable.sync import compute_diff, entry_id, SyncPlan

_E1 = TimetableEntry(
    date=date(2025, 3, 10),
    start_time=time(8, 0),
    end_time=time(9, 30),
    subject="Matematyka",
    lecture_type="wykład",
    lecturer="Dr Kowalski",
    room="s. A101",
    groups="GR1",
)
_E2 = TimetableEntry(
    date=date(2025, 3, 11),
    start_time=time(10, 0),
    end_time=time(11, 30),
    subject="Fizyka",
    lecture_type="lab.",
    lecturer="Prof. Nowak",
    room="s. B202",
    groups="GR2",
)


def _make_event(entry: TimetableEntry, google_id: str = "gcal-id-1") -> dict:
    eid = entry_id(entry)
    from pk_timetable.gcal import _entry_to_event
    body = _entry_to_event(entry, eid, "Europe/Warsaw")
    return {"id": google_id, **body}


def test_entry_id_is_stable() -> None:
    assert entry_id(_E1) == entry_id(_E1)


def test_entry_id_differs_for_different_entries() -> None:
    assert entry_id(_E1) != entry_id(_E2)


def test_all_new_entries_go_to_create() -> None:
    plan = compute_diff([_E1, _E2], [])
    assert len(plan.to_create) == 2
    assert plan.to_update == []
    assert plan.to_delete == []


def test_unchanged_entry_is_skipped() -> None:
    existing = [_make_event(_E1)]
    plan = compute_diff([_E1], existing)
    assert plan.is_empty()


def test_deleted_entry_goes_to_delete() -> None:
    existing = [_make_event(_E1, "gcal-1"), _make_event(_E2, "gcal-2")]
    plan = compute_diff([_E1], existing)  # _E2 removed from timetable
    assert plan.to_delete == ["gcal-2"]
    assert plan.to_create == []
    assert plan.to_update == []


def test_changed_entry_goes_to_update() -> None:
    existing = [_make_event(_E1, "gcal-1")]
    modified = TimetableEntry(
        date=_E1.date,
        start_time=_E1.start_time,
        end_time=_E1.end_time,
        subject=_E1.subject,
        lecture_type=_E1.lecture_type,
        lecturer=_E1.lecturer,
        room="s. NEW-ROOM",  # room changed
        groups=_E1.groups,
    )
    plan = compute_diff([modified], existing)
    assert len(plan.to_update) == 1
    assert plan.to_update[0][0] == "gcal-1"
    assert plan.to_create == []
    assert plan.to_delete == []


def test_mixed_plan() -> None:
    existing = [_make_event(_E1, "gcal-1")]
    plan = compute_diff([_E2], existing)  # _E1 deleted, _E2 added
    assert len(plan.to_create) == 1
    assert plan.to_create[0].subject == "Fizyka"
    assert plan.to_delete == ["gcal-1"]
    assert plan.to_update == []

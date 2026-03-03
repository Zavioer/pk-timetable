from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass

from pk_timetable.gcal import GCalClient, _ENTRY_ID_KEY
from pk_timetable.parser import TimetableEntry

logger = logging.getLogger(__name__)


def entry_id(entry: TimetableEntry) -> str:
    """Stable 16-char ID derived from the immutable identity fields of an entry."""
    key = f"{entry.date}|{entry.start_time}|{entry.subject}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _event_matches(entry: TimetableEntry, event: dict) -> bool:
    """Return True if an existing calendar event already reflects *entry* exactly."""
    from pk_timetable.gcal import _dt, _build_description
    summary_ok = event.get("summary", "") == entry.subject
    location_ok = event.get("location", "") == entry.room
    description_ok = event.get("description", "") == _build_description(entry)

    start = (event.get("start") or {}).get("dateTime", "")
    end = (event.get("end") or {}).get("dateTime", "")
    start_ok = start.startswith(_dt(entry.date, entry.start_time))
    end_ok = end.startswith(_dt(entry.date, entry.end_time))

    return summary_ok and location_ok and description_ok and start_ok and end_ok


@dataclass
class SyncPlan:
    to_create: list[TimetableEntry]
    to_update: list[tuple[str, TimetableEntry]]  # (google_event_id, entry)
    to_delete: list[str]  # google_event_ids

    def is_empty(self) -> bool:
        return not self.to_create and not self.to_update and not self.to_delete

    def summary(self) -> str:
        return f"create={len(self.to_create)}, update={len(self.to_update)}, delete={len(self.to_delete)}"


def compute_diff(entries: list[TimetableEntry], existing_events: list[dict]) -> SyncPlan:
    """Diff *entries* against *existing_events* and produce a minimal SyncPlan."""

    # Build lookup: entry_id → google event
    event_by_entry_id: dict[str, dict] = {}
    for ev in existing_events:
        eid = (ev.get("extendedProperties") or {}).get("private", {}).get(_ENTRY_ID_KEY)
        if eid:
            event_by_entry_id[eid] = ev

    # Build set of entry_ids from the new timetable
    timetable_ids: set[str] = set()
    to_create: list[TimetableEntry] = []
    to_update: list[tuple[str, TimetableEntry]] = []

    for e in entries:
        eid = entry_id(e)
        timetable_ids.add(eid)
        if eid not in event_by_entry_id:
            to_create.append(e)
        elif not _event_matches(e, event_by_entry_id[eid]):
            to_update.append((event_by_entry_id[eid]["id"], e))

    # Events in calendar that no longer exist in timetable → delete
    to_delete = [
        ev["id"]
        for eid, ev in event_by_entry_id.items()
        if eid not in timetable_ids
    ]

    plan = SyncPlan(to_create=to_create, to_update=to_update, to_delete=to_delete)
    logger.info("Sync plan: %s", plan.summary())
    return plan


_API_DELAY = 0.15  # seconds between API calls — stays well under the 10 req/s limit


def apply_sync_plan(plan: SyncPlan, client: GCalClient) -> None:
    for e in plan.to_create:
        client.create_event(e, entry_id(e))
        time.sleep(_API_DELAY)

    for google_id, e in plan.to_update:
        client.update_event(google_id, e, entry_id(e))
        time.sleep(_API_DELAY)

    for google_id in plan.to_delete:
        client.delete_event(google_id)
        time.sleep(_API_DELAY)

    logger.info("Applied sync plan: %s", plan.summary())

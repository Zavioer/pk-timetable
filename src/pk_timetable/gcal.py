from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from pk_timetable.parser import TimetableEntry

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/calendar"]
_SOURCE_KEY = "source"
_SOURCE_VALUE = "pk-timetable"
_ENTRY_ID_KEY = "entry_id"


def _dt(d: date, t: time) -> str:
    """Format a date+time pair as an RFC 3339 string (local timezone assumed naive)."""
    return datetime.combine(d, t).isoformat()


_LECTURE_TYPE_LABELS: dict[str, str] = {
    "wykład": "Wykład",
    "wyklad": "Wykład",
    "lab.": "Lab",
    "lab": "Lab",
    "laboratorium": "Lab",
    "p": "Projekt",
    "projekt": "Projekt",
    "ćwiczenia": "Ćwiczenia",
    "ćw.": "Ćwiczenia",
    "cwiczenia": "Ćwiczenia",
}


def _build_summary(entry: TimetableEntry) -> str:
    if not entry.lecture_type:
        return entry.subject
    label = _LECTURE_TYPE_LABELS.get(entry.lecture_type.lower().strip(), entry.lecture_type.strip(" .").capitalize())
    return f"[{label}] {entry.subject}"


def _build_description(entry: TimetableEntry) -> str:
    return "\n".join(filter(None, [entry.lecture_type, entry.lecturer]))


def _entry_to_event(entry: TimetableEntry, entry_id: str, timezone: str) -> dict[str, Any]:
    return {
        "summary": _build_summary(entry),
        "location": entry.room,
        "description": _build_description(entry),
        "start": {"dateTime": _dt(entry.date, entry.start_time), "timeZone": timezone},
        "end": {"dateTime": _dt(entry.date, entry.end_time), "timeZone": timezone},
        "extendedProperties": {
            "private": {
                _SOURCE_KEY: _SOURCE_VALUE,
                _ENTRY_ID_KEY: entry_id,
            }
        },
    }


class GCalClient:
    def __init__(self, credentials_path: Path, calendar_id: str, timezone: str) -> None:
        self._timezone = timezone
        creds = service_account.Credentials.from_service_account_file(
            str(credentials_path), scopes=_SCOPES
        )
        self._service = build("calendar", "v3", credentials=creds)
        self._calendar_id = calendar_id

    def list_managed_events(self, time_min: date, time_max: date) -> list[dict[str, Any]]:
        """Return all events created by this tool within the given date range."""
        time_min_str = datetime.combine(time_min, time(0, 0), tzinfo=timezone.utc).isoformat()
        time_max_str = datetime.combine(time_max, time(23, 59, 59), tzinfo=timezone.utc).isoformat()

        events: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            result = (
                self._service.events()
                .list(
                    calendarId=self._calendar_id,
                    timeMin=time_min_str,
                    timeMax=time_max_str,
                    privateExtendedProperty=f"{_SOURCE_KEY}={_SOURCE_VALUE}",
                    pageToken=page_token,
                    singleEvents=True,
                )
                .execute()
            )
            events.extend(result.get("items", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                break

        logger.info("Found %d managed events in calendar", len(events))
        return events

    def create_event(self, entry: TimetableEntry, entry_id: str) -> None:
        body = _entry_to_event(entry, entry_id, self._timezone)
        self._service.events().insert(calendarId=self._calendar_id, body=body).execute()
        logger.debug("Created event: %s on %s", entry.subject, entry.date)

    def update_event(self, event_id: str, entry: TimetableEntry, entry_id: str) -> None:
        body = _entry_to_event(entry, entry_id, self._timezone)
        self._service.events().update(
            calendarId=self._calendar_id, eventId=event_id, body=body
        ).execute()
        logger.debug("Updated event: %s on %s", entry.subject, entry.date)

    def delete_event(self, event_id: str) -> None:
        self._service.events().delete(
            calendarId=self._calendar_id, eventId=event_id
        ).execute()
        logger.debug("Deleted event id=%s", event_id)

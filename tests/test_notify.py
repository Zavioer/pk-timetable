from __future__ import annotations

from datetime import date, time

import pytest
import requests

from pk_timetable.notify import format_sync_message, send_discord, _DISCORD_MAX_LENGTH
from pk_timetable.parser import TimetableEntry
from pk_timetable.sync import SyncPlan

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

_EXISTING_EVENT = {
    "id": "gcal-del-1",
    "summary": "[Wykład] Matematyka",
    "start": {"dateTime": "2025-03-10T08:00:00"},
    "end": {"dateTime": "2025-03-10T09:30:00"},
}


# ---------------------------------------------------------------------------
# format_sync_message — pure function tests
# ---------------------------------------------------------------------------

def test_create_only_plan() -> None:
    plan = SyncPlan(to_create=[_E1], to_update=[], to_delete=[])
    msg = format_sync_message(plan, {})
    assert "1 change" in msg
    assert "changes" not in msg  # singular
    assert "➕" in msg
    assert "[Wykład] Matematyka" in msg
    assert "Mon 10 Mar" in msg
    assert "08:00–09:30" in msg


def test_update_only_plan() -> None:
    plan = SyncPlan(to_create=[], to_update=[("gcal-1", _E2)], to_delete=[])
    msg = format_sync_message(plan, {})
    assert "1 change" in msg
    assert "✏️" in msg
    assert "[Lab] Fizyka" in msg
    assert "Tue 11 Mar" in msg
    assert "10:00–11:30" in msg


def test_delete_only_plan_uses_event_by_id() -> None:
    plan = SyncPlan(to_create=[], to_update=[], to_delete=["gcal-del-1"])
    msg = format_sync_message(plan, {"gcal-del-1": _EXISTING_EVENT})
    assert "1 change" in msg
    assert "🗑️" in msg
    assert "[Wykład] Matematyka" in msg
    assert "Mon 10 Mar" in msg
    assert "08:00–09:30" in msg


def test_plural_header_for_multiple_changes() -> None:
    plan = SyncPlan(to_create=[_E1, _E2], to_update=[], to_delete=[])
    msg = format_sync_message(plan, {})
    assert "2 changes" in msg


def test_mixed_plan_contains_all_prefixes() -> None:
    plan = SyncPlan(
        to_create=[_E1],
        to_update=[("gcal-upd-1", _E2)],
        to_delete=["gcal-del-1"],
    )
    msg = format_sync_message(plan, {"gcal-del-1": _EXISTING_EVENT})
    assert "3 changes" in msg
    assert "➕" in msg
    assert "✏️" in msg
    assert "🗑️" in msg


def test_deleted_event_missing_from_event_by_id() -> None:
    plan = SyncPlan(to_create=[], to_update=[], to_delete=["unknown-id"])
    msg = format_sync_message(plan, {})
    assert "🗑️" in msg
    assert "**?**" in msg


def test_deleted_event_with_missing_datetime_falls_back_gracefully() -> None:
    broken_event = {"id": "gcal-x", "summary": "Sieci komputerowe"}  # no start/end
    plan = SyncPlan(to_create=[], to_update=[], to_delete=["gcal-x"])
    msg = format_sync_message(plan, {"gcal-x": broken_event})
    assert "🗑️" in msg
    assert "Sieci komputerowe" in msg


def test_long_message_is_truncated_to_discord_limit() -> None:
    # Generate enough entries to exceed 2000 chars
    entries = [
        TimetableEntry(
            date=date(2025, 3, 10),
            start_time=time(8, 0),
            end_time=time(9, 30),
            subject=f"Przedmiot numer {i} z bardzo długą nazwą żeby wypełnić limit",
            lecture_type="wykład",
            lecturer="Dr X",
            room="s. A1",
            groups="GR1",
        )
        for i in range(50)
    ]
    plan = SyncPlan(to_create=entries, to_update=[], to_delete=[])
    msg = format_sync_message(plan, {})
    assert len(msg) <= _DISCORD_MAX_LENGTH
    assert "…and more" in msg
    assert "50 changes" in msg


# ---------------------------------------------------------------------------
# send_discord — HTTP layer tests
# ---------------------------------------------------------------------------

def test_send_discord_posts_correct_payload(mocker) -> None:
    mock_post = mocker.patch("pk_timetable.notify.requests.post")
    mock_post.return_value.raise_for_status = lambda: None

    send_discord("https://discord.example.com/webhook", "hello")

    mock_post.assert_called_once_with(
        "https://discord.example.com/webhook",
        json={"content": "hello"},
        timeout=10,
    )


def test_send_discord_calls_raise_for_status(mocker) -> None:
    mock_post = mocker.patch("pk_timetable.notify.requests.post")
    mock_post.return_value.raise_for_status = mocker.Mock()

    send_discord("https://discord.example.com/webhook", "hello")

    mock_post.return_value.raise_for_status.assert_called_once()


def test_send_discord_swallows_connection_error(mocker) -> None:
    mock_post = mocker.patch("pk_timetable.notify.requests.post")
    mock_post.side_effect = requests.ConnectionError("unreachable")

    send_discord("https://discord.example.com/webhook", "hello")  # must not raise


def test_send_discord_swallows_http_error(mocker) -> None:
    mock_post = mocker.patch("pk_timetable.notify.requests.post")
    mock_post.return_value.raise_for_status = mocker.Mock(
        side_effect=requests.HTTPError("403 Forbidden")
    )

    send_discord("https://discord.example.com/webhook", "hello")  # must not raise


def test_send_discord_logs_warning_on_failure(mocker, caplog) -> None:
    import logging
    mock_post = mocker.patch("pk_timetable.notify.requests.post")
    mock_post.side_effect = requests.ConnectionError("timeout")

    with caplog.at_level(logging.WARNING, logger="pk_timetable.notify"):
        send_discord("https://discord.example.com/webhook", "hello")

    assert any("Failed to send Discord notification" in r.message for r in caplog.records)

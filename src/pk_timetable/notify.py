from __future__ import annotations

import logging
from datetime import datetime

import requests

from pk_timetable.gcal import _build_summary
from pk_timetable.parser import TimetableEntry
from pk_timetable.sync import SyncPlan

logger = logging.getLogger(__name__)

_DISCORD_MAX_LENGTH = 2000


def _fmt_entry(entry: TimetableEntry) -> str:
    d = entry.date.strftime("%a %d %b")
    t = f"{entry.start_time.strftime('%H:%M')}–{entry.end_time.strftime('%H:%M')}"
    return f"**{_build_summary(entry)}** — {d} {t}"


def _fmt_event(event: dict) -> str:
    summary = event.get("summary", "?")
    start_dt = (event.get("start") or {}).get("dateTime", "")
    end_dt = (event.get("end") or {}).get("dateTime", "")
    try:
        start = datetime.fromisoformat(start_dt)
        end = datetime.fromisoformat(end_dt)
        d = start.strftime("%a %d %b")
        t = f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"
        return f"**{summary}** — {d} {t}"
    except (ValueError, TypeError):
        return f"**{summary}**"


def format_sync_message(plan: SyncPlan, event_by_id: dict[str, dict]) -> str:
    total = len(plan.to_create) + len(plan.to_update) + len(plan.to_delete)
    lines = [f"**Timetable updated** — {total} change{'s' if total != 1 else ''}"]

    for entry in plan.to_create:
        lines.append(f"➕ {_fmt_entry(entry)}")

    for _gid, entry in plan.to_update:
        lines.append(f"✏️ {_fmt_entry(entry)}")

    for gid in plan.to_delete:
        ev = event_by_id.get(gid, {})
        lines.append(f"🗑️ {_fmt_event(ev)}")

    message = "\n".join(lines)
    if len(message) > _DISCORD_MAX_LENGTH:
        truncated = f"\n…and more (total {total} changes)"
        cutoff = _DISCORD_MAX_LENGTH - len(truncated)
        message = message[:cutoff].rsplit("\n", 1)[0] + truncated

    return message


def send_discord(webhook_url: str, message: str) -> None:
    try:
        resp = requests.post(webhook_url, json={"content": message}, timeout=10)
        resp.raise_for_status()
        logger.debug("Discord notification sent")
    except requests.RequestException as exc:
        logger.warning("Failed to send Discord notification: %s", exc)

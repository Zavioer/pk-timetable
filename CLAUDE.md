# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Daily automation: fetch a university timetable `.xlsx` from a URL → detect changes via SHA-256 hash → if changed, diff against existing Google Calendar events → apply minimal create/update/delete operations to a specified Google Calendar sub-calendar. Events managed by this tool are tagged via `extendedProperties.private.source = "pk-timetable"` so manually added events are never touched.

## Commands

```bash
# Install dependencies and dev tools
uv sync --dev

# Run the sync (requires config.yaml + service account credentials)
uv run pk-timetable

# Dry run — print what would change without calling Google Calendar
uv run pk-timetable --dry-run

# Force sync even if the timetable hash hasn't changed
uv run pk-timetable --force

# Run tests
uv run pytest

# Run a single test file
uv run pytest tests/test_sync.py -v
```

## Architecture

```
src/pk_timetable/
├── main.py      # CLI entry point; orchestrates the full workflow
├── config.py    # Pydantic models for config.yaml; load_config()
├── fetcher.py   # HTTP download + SHA-256 change detection (state/last_hash.txt)
├── parser.py    # xlsx bytes → list[TimetableEntry]; column mapping from config
├── gcal.py      # GCalClient wrapping Google Calendar API (Service Account auth)
└── sync.py      # compute_diff() → SyncPlan; apply_sync_plan()
```

**Data flow:** `fetcher.fetch()` → `fetcher.has_changed()` → `parser.parse()` → `gcal.list_managed_events()` → `sync.compute_diff()` → `sync.apply_sync_plan()` → `fetcher.save_hash()`

**Hash is saved last** — if syncing fails partway through, the next run retries the full sync.

## Configuration

Copy `config.yaml` and fill in your values. Column mapping accepts 0-based integer indices or exact header names from the xlsx. The `.xlsx` format/column layout is provided at runtime via `config.yaml` — no code changes needed when the file format changes.

## Credentials

Place the Google service account JSON at `credentials/service_account.json` (gitignored). The service account must have the Calendar API enabled and be granted access to the target calendar.

## Stable event identity

`sync.entry_id(entry)` computes `sha256(date|start_time|subject)[:16]` and stores it in `extendedProperties.private.entry_id`. This is how the diff matches timetable rows to existing Google Calendar events across runs.

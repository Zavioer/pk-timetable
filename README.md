# pk-timetable

Syncs a university timetable from an `.xls` file to a Google Calendar sub-calendar.
It detects changes via SHA-256 hashing and applies only the minimal set of create/update/delete operations.
Manually added calendar events are never touched — only events created by this tool are managed.

## Configuration

Copy `config.yaml` and fill in your values:

```yaml
timetable_url: "https://example.com/timetable.xls"   # URL to download the timetable file
calendar_id: "your-id@group.calendar.google.com"      # target Google Calendar ID
credentials_path: "credentials/service_account.json"  # Google service account key file
state_dir: "state"                                     # directory for caching the last hash

layout:
  first_block_row: 7      # 1-indexed row of the first day-block header (group names)
  block_height: 13        # rows per day block (1 header + 12 data)
  time_slot_height: 3     # rows per time slot (cells are merged across 3 rows)
  date_col: "Q"           # column containing the date (merged across all data rows)
  time_col: "R"           # column containing the time range, e.g. "8.00-10.30"
  group_col: "T"          # group column to extract — change to U, V, W, X, or Y for other groups
```

Place the Google service account JSON at `credentials/service_account.json`.
The service account must have the Calendar API enabled and editor access to the target calendar.

### Discord notifications (optional)

Set `DISCORD_WEBHOOK_URL` in your `.env` file (or as an environment variable) to receive a message in Discord after each sync that produces changes. The message lists every created (➕), updated (✏️), and deleted (🗑️) event with its title, date, and time range.

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Get the URL from your Discord channel: **Settings → Integrations → Webhooks → New Webhook → Copy Webhook URL**. Failures to deliver the notification are logged as warnings but never abort the sync.

### Running

```bash
uv run pk-timetable              # normal sync
uv run pk-timetable --dry-run    # preview changes without writing to the calendar
uv run pk-timetable --force      # sync even if the timetable file has not changed
```

## Development

### Testing

```bash
# Run all tests with coverage report
uv run pytest --cov=pk_timetable --cov-report=html

# Open the report (generated in htmlcov/)
xdg-open htmlcov/index.html   # Linux
open htmlcov/index.html        # macOS
```

Integration tests require `tests/resources/test_calendar.xls` and a configured `config.yaml`;
they are skipped automatically when those files are absent.
To run only unit tests:

```bash
uv run pytest -m "not integration"
```


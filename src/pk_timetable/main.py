from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from pk_timetable.config import load_config
from pk_timetable import fetcher, parser
from pk_timetable.gcal import GCalClient
from pk_timetable.sync import apply_sync_plan, compute_diff

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Sync PK timetable (.xlsx) to Google Calendar")
    p.add_argument("--config", default="config.yaml", help="Path to config.yaml (default: config.yaml)")
    p.add_argument("--dry-run", action="store_true", help="Print sync plan without applying it")
    p.add_argument("--force", action="store_true", help="Skip change detection and always sync")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    cfg = load_config(args.config)
    cfg.state_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch
    data = fetcher.fetch(cfg.timetable_url)

    # 2. Change detection
    if not args.force and not fetcher.has_changed(data, cfg.state_dir):
        logger.info("Timetable unchanged — nothing to do")
        return 0

    # 3. Parse
    entries = parser.parse(data, cfg.columns)
    if not entries:
        logger.warning("No entries parsed from timetable; aborting to avoid data loss")
        return 1

    # 4. Fetch existing calendar events (cover 2 years from today)
    today = date.today()
    time_max = today + timedelta(days=730)

    if args.dry_run:
        logger.info("DRY RUN — skipping Google Calendar API calls")
        logger.info("Would sync %d timetable entries", len(entries))
        return 0

    client = GCalClient(cfg.credentials_path, cfg.calendar_id)
    existing = client.list_managed_events(time_min=today - timedelta(days=30), time_max=time_max)

    # 5. Diff
    plan = compute_diff(entries, existing)

    if plan.is_empty():
        logger.info("Calendar already up to date")
        fetcher.save_hash(data, cfg.state_dir)
        return 0

    # 6. Apply
    apply_sync_plan(plan, client)

    # 7. Persist hash only after a fully successful sync
    fetcher.save_hash(data, cfg.state_dir)
    logger.info("Sync complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())

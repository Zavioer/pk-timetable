from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

# Env-var → config field mapping (env var takes precedence over config.yaml)
_ENV_OVERRIDES: list[tuple[str, str]] = [
    ("GOOGLE_CALENDAR_ID", "calendar_id"),
    ("TIMETABLE_URL", "timetable_url"),
    ("GOOGLE_APPLICATION_CREDENTIALS", "credentials_path"),
]


class LayoutConfig(BaseModel):
    first_block_row: int = 7        # 1-indexed row of the first block's header line
    block_height: int = 13          # rows per day block (1 header + 12 data)
    time_slot_height: int = 3       # rows per time slot
    date_col: str | int = "Q"       # column holding the date (merged in data rows)
    time_col: str | int = "R"       # column holding the time range, e.g. "8.00-10.30"
    group_col: str | int = "T"      # which group column to extract subjects from


class Config(BaseModel):
    timetable_url: str
    calendar_id: str
    credentials_path: Path
    state_dir: Path = Path("state")
    layout: LayoutConfig


def load_config(path: Path | str = "config.yaml") -> Config:
    load_dotenv()  # no-op if .env is absent; never overrides already-set env vars
    with open(path) as fh:
        raw = yaml.safe_load(fh)
    for env_key, config_key in _ENV_OVERRIDES:
        value = os.environ.get(env_key)
        if value:
            raw[config_key] = value
    return Config.model_validate(raw)

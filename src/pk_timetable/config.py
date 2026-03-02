from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


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
    with open(path) as fh:
        raw = yaml.safe_load(fh)
    return Config.model_validate(raw)

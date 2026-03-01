from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator


class ColumnMap(BaseModel):
    date: int | str
    start_time: int | str
    end_time: int | str
    subject: int | str
    room: int | str | None = None
    lecturer: int | str | None = None
    groups: int | str | None = None
    header_row: int = 0


class Config(BaseModel):
    timetable_url: str
    calendar_id: str
    credentials_path: Path
    state_dir: Path = Path("state")
    columns: ColumnMap

    @field_validator("credentials_path", "state_dir", mode="before")
    @classmethod
    def to_path(cls, v: object) -> Path:
        return Path(str(v))


def load_config(path: Path | str = "config.yaml") -> Config:
    with open(path) as fh:
        raw = yaml.safe_load(fh)
    return Config.model_validate(raw)

from __future__ import annotations

from pathlib import Path

import pytest

from pk_timetable.config import load_config, Config
from pk_timetable.parser import _xls_to_xlsx, _XLS_MAGIC

_RESOURCES = Path(__file__).parent.parent / "resources"
_CONFIG_PATH = Path("config.yaml")

# Accept either format; .xls is converted transparently to xlsx bytes.
_CANDIDATES = [
    _RESOURCES / "test_calendar.xlsx",
    _RESOURCES / "test_calendar.xls",
]


@pytest.fixture(scope="session")
def integration_config() -> Config:
    if not _CONFIG_PATH.exists():
        pytest.skip(f"config.yaml not found — place it at {_CONFIG_PATH.resolve()}")
    return load_config(_CONFIG_PATH)


@pytest.fixture(scope="session")
def timetable_bytes() -> bytes:
    for path in _CANDIDATES:
        if path.exists():
            raw = path.read_bytes()
            if raw[:4] == _XLS_MAGIC:
                return _xls_to_xlsx(raw)
            return raw
    paths = ", ".join(str(p) for p in _CANDIDATES)
    pytest.skip(f"No test timetable found — place one at: {paths}")

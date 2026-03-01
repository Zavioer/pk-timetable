from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_HASH_FILE = "last_hash.txt"


def fetch(url: str, timeout: int = 30) -> bytes:
    """Download the xlsx file from *url* and return its raw bytes."""
    logger.info("Fetching timetable from %s", url)
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def has_changed(data: bytes, state_dir: Path) -> bool:
    """Return True if *data* differs from the previously saved hash."""
    hash_file = state_dir / _HASH_FILE
    new_hash = _hash(data)
    if not hash_file.exists():
        logger.debug("No previous hash found — treating as changed")
        return True
    old_hash = hash_file.read_text().strip()
    changed = new_hash != old_hash
    logger.debug("Hash check: %s (old=%s, new=%s)", "CHANGED" if changed else "same", old_hash[:8], new_hash[:8])
    return changed


def save_hash(data: bytes, state_dir: Path) -> None:
    """Persist the SHA-256 hash of *data* to disk."""
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / _HASH_FILE).write_text(_hash(data))
    logger.debug("Saved new hash to %s", state_dir / _HASH_FILE)

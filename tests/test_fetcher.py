from __future__ import annotations

from pathlib import Path

import pytest

from pk_timetable import fetcher


def test_has_changed_no_state_file(tmp_path: Path) -> None:
    assert fetcher.has_changed(b"data", tmp_path) is True


def test_has_changed_same_data(tmp_path: Path) -> None:
    data = b"same content"
    fetcher.save_hash(data, tmp_path)
    assert fetcher.has_changed(data, tmp_path) is False


def test_has_changed_different_data(tmp_path: Path) -> None:
    fetcher.save_hash(b"old content", tmp_path)
    assert fetcher.has_changed(b"new content", tmp_path) is True


def test_save_hash_creates_dir(tmp_path: Path) -> None:
    state_dir = tmp_path / "new" / "nested"
    fetcher.save_hash(b"x", state_dir)
    assert (state_dir / "last_hash.txt").exists()


def test_fetch_returns_bytes(mocker) -> None:
    mock_get = mocker.patch("pk_timetable.fetcher.requests.get")
    mock_get.return_value.content = b"xlsx bytes"
    mock_get.return_value.raise_for_status = lambda: None

    result = fetcher.fetch("https://example.com/file.xlsx")
    assert result == b"xlsx bytes"
    mock_get.assert_called_once_with("https://example.com/file.xlsx", timeout=30)

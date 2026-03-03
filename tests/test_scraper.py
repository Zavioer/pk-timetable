from __future__ import annotations

import pytest

from pk_timetable.scraper import find_timetable_url

_BASE = "https://it.pk.edu.pl/rozklady/"

# Two H2 sections, each with an Informatyka link — mirrors the real page structure.
_HTML_TWO_SECTIONS = """
<html><body>
<h2>STUDIA STACJONARNE</h2>
<ul>
  <li><a href="/uploads/STACJONARNE.xls">Kierunek: Informatyka – pobierz (aktualizacja 01-03-2026)</a></li>
  <li><a href="/uploads/MATEMATYKA-S.xls">Kierunek: Matematyka – pobierz</a></li>
</ul>
<h2>STUDIA NIESTACJONARNE</h2>
<ul>
  <li><a href="/uploads/NIESTACJONARNE.xls">Kierunek: Informatyka – pobierz (aktualizacja 01-03-2026)</a></li>
  <li><a href="/uploads/MATEMATYKA-N.xls">Kierunek: Matematyka – pobierz</a></li>
</ul>
<h2>Inne</h2>
</body></html>
"""

_HTML_ONE_SECTION = """
<html><body>
<h2>STUDIA NIESTACJONARNE</h2>
<a href="https://example.com/timetable.xls">Kierunek: Informatyka – pobierz (aktualizacja 15-01-2026)</a>
</body></html>
"""

_HTML_RELATIVE = """
<html><body>
<h2>STUDIA NIESTACJONARNE</h2>
<a href="../files/plan.xls">Informatyka pobierz</a>
</body></html>
"""

_HTML_NO_INFORMATYKA = """
<html><body>
<h2>STUDIA NIESTACJONARNE</h2>
<a href="/other.xls">Kierunek: Fizyka – pobierz</a>
</body></html>
"""


def _mock_get(mocker, html: str):
    mock = mocker.patch("pk_timetable.scraper.requests.get")
    mock.return_value.text = html
    mock.return_value.raise_for_status = lambda: None
    return mock


def test_section_scoping_picks_niestacjonarne_link(mocker) -> None:
    _mock_get(mocker, _HTML_TWO_SECTIONS)
    url = find_timetable_url(_BASE, r"Informatyka.*pobierz", "STUDIA NIESTACJONARNE")
    assert "NIESTACJONARNE" in url


def test_section_scoping_picks_stacjonarne_link(mocker) -> None:
    _mock_get(mocker, _HTML_TWO_SECTIONS)
    url = find_timetable_url(_BASE, r"Informatyka.*pobierz", "STUDIA STACJONARNE")
    assert "STACJONARNE" in url
    assert "NIESTACJONARNE" not in url


def test_no_section_pattern_returns_first_match(mocker) -> None:
    _mock_get(mocker, _HTML_TWO_SECTIONS)
    url = find_timetable_url(_BASE, r"Informatyka.*pobierz")
    assert "STACJONARNE" in url


def test_finds_link_without_section_pattern(mocker) -> None:
    _mock_get(mocker, _HTML_ONE_SECTION)
    url = find_timetable_url(_BASE, r"Informatyka.*pobierz")
    assert url == "https://example.com/timetable.xls"


def test_relative_href_resolved_to_absolute(mocker) -> None:
    _mock_get(mocker, _HTML_RELATIVE)
    url = find_timetable_url(_BASE, r"Informatyka.*pobierz", "STUDIA NIESTACJONARNE")
    assert url.startswith("https://")
    assert url.endswith("plan.xls")


def test_raises_when_text_not_found_in_section(mocker) -> None:
    _mock_get(mocker, _HTML_NO_INFORMATYKA)
    with pytest.raises(ValueError, match="No timetable link found"):
        find_timetable_url(_BASE, r"Informatyka.*pobierz", "STUDIA NIESTACJONARNE")


def test_raises_when_section_not_found(mocker) -> None:
    _mock_get(mocker, _HTML_ONE_SECTION)
    with pytest.raises(ValueError, match="No timetable link found"):
        find_timetable_url(_BASE, r"Informatyka.*pobierz", "STUDIA STACJONARNE")


def test_match_is_case_insensitive(mocker) -> None:
    _mock_get(mocker, _HTML_ONE_SECTION)
    url = find_timetable_url(_BASE, r"informatyka.*POBIERZ", "studia niestacjonarne")
    assert url == "https://example.com/timetable.xls"

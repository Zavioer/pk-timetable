from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


class _Parser(HTMLParser):
    """Collect (href, text) pairs for <a> tags scoped to an H2 section.

    When *section_pattern* is given only links that appear *after* an H2 whose
    text matches the pattern (and *before* the next H2) are collected.
    When *section_pattern* is empty every link on the page is collected.
    """

    def __init__(self, section_pattern: re.Pattern[str] | None) -> None:
        super().__init__()
        self._section_re = section_pattern
        self._links: list[tuple[str, str]] = []
        self._in_section: bool = section_pattern is None
        self._in_h2: bool = False
        self._h2_buf: list[str] = []
        self._current_href: str | None = None
        self._a_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "h2":
            self._in_h2 = True
            self._h2_buf = []
        elif tag == "a" and self._in_section and not self._in_h2:
            self._current_href = dict(attrs).get("href") or ""
            self._a_buf = []

    def handle_data(self, data: str) -> None:
        if self._in_h2:
            self._h2_buf.append(data)
        elif self._current_href is not None:
            self._a_buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2":
            h2_text = "".join(self._h2_buf).strip()
            self._in_h2 = False
            if self._section_re is not None:
                self._in_section = bool(self._section_re.search(h2_text))
        elif tag == "a" and self._current_href is not None:
            self._links.append((self._current_href, "".join(self._a_buf).strip()))
            self._current_href = None
            self._a_buf = []

    @property
    def links(self) -> list[tuple[str, str]]:
        return self._links


def find_timetable_url(
    page_url: str,
    link_text_pattern: str,
    section_heading_pattern: str = "",
    timeout: int = 30,
) -> str:
    """Scrape *page_url* and return the absolute href of the first matching link.

    If *section_heading_pattern* is non-empty only links inside the H2 section
    whose heading text matches that pattern are considered.  Within that
    section the first link whose visible text matches *link_text_pattern*
    (both patterns are case-insensitive regexes) is returned.

    Raises ValueError if no matching link is found.
    """
    logger.info("Scraping timetable link from %s", page_url)
    response = requests.get(
        page_url,
        timeout=timeout,
        headers={"User-Agent": "pk-timetable-bot/1.0"},
    )
    response.raise_for_status()

    section_re = re.compile(section_heading_pattern, re.IGNORECASE) if section_heading_pattern else None
    parser = _Parser(section_re)
    parser.feed(response.text)

    text_re = re.compile(link_text_pattern, re.IGNORECASE)
    for href, text in parser.links:
        if text_re.search(text):
            url = urljoin(page_url, href)
            logger.info("Found timetable link: %s", url)
            return url

    patterns = f"text={link_text_pattern!r}"
    if section_heading_pattern:
        patterns += f", section={section_heading_pattern!r}"
    raise ValueError(f"No timetable link found on {page_url!r} matching {patterns}")

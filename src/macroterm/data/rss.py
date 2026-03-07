from __future__ import annotations

import html as html_mod
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime

import httpx

from macroterm.data.cache import async_ttl_cache

FEEDS: dict[str, str] = {
    "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
    "BEA": "https://apps.bea.gov/rss/rss.xml",
    "Census Bureau": "https://www.census.gov/economic-indicators/indicator.xml",
    "ECB": "https://www.ecb.europa.eu/rss/press.html",
    "ECB Blog": "https://www.ecb.europa.eu/rss/blog.html",
    "BIS Speeches": "https://www.bis.org/doclist/cbspeeches.rss",
}


@dataclass
class RSSEvent:
    title: str
    source: str
    date: str
    link: str
    description: str


def _parse_pub_date(raw: str) -> datetime | None:
    """Parse RFC 2822 date from pubDate element."""
    try:
        return parsedate_to_datetime(raw)
    except Exception:
        return None


def _parse_iso_date(raw: str) -> datetime | None:
    """Parse ISO 8601 date from dc:date element."""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


_RSS1_NS = {"rss1": "http://purl.org/rss/1.0/", "dc": "http://purl.org/dc/elements/1.1/"}


def _parse_feed(xml_text: str, source: str) -> list[RSSEvent]:
    """Parse RSS 2.0 or RSS 1.0 (RDF) XML into RSSEvent list."""
    root = ET.fromstring(xml_text)
    events: list[RSSEvent] = []

    # Try RSS 2.0 first, fall back to RSS 1.0 (RDF with namespaces)
    items = root.findall(".//item")
    if items:
        for item in items:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            description = (item.findtext("description") or "").strip()
            pub_date_raw = (item.findtext("pubDate") or "").strip()

            dt = _parse_pub_date(pub_date_raw)
            date_str = dt.strftime("%Y-%m-%d") if dt else ""

            events.append(RSSEvent(
                title=title, source=source, date=date_str,
                link=link, description=description,
            ))
    else:
        for item in root.findall(".//rss1:item", _RSS1_NS):
            title = (item.findtext("rss1:title", namespaces=_RSS1_NS) or "").strip()
            link = (item.findtext("rss1:link", namespaces=_RSS1_NS) or "").strip()
            description = (item.findtext("rss1:description", namespaces=_RSS1_NS) or "").strip()
            dc_date = (item.findtext("dc:date", namespaces=_RSS1_NS) or "").strip()

            dt = _parse_iso_date(dc_date)
            date_str = dt.strftime("%Y-%m-%d") if dt else ""

            events.append(RSSEvent(
                title=title, source=source, date=date_str,
                link=link, description=description,
            ))

    return events


@async_ttl_cache(1800)
async def _fetch_feed(source: str, url: str) -> list[RSSEvent]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=15, follow_redirects=True)
        resp.raise_for_status()
    return _parse_feed(resp.text, source)


async def get_rss_events() -> list[RSSEvent]:
    """Fetch all RSS feeds and return events sorted by date descending."""
    all_events: list[RSSEvent] = []
    for source, url in FEEDS.items():
        try:
            events = await _fetch_feed(source, url)
            all_events.extend(events)
        except Exception:
            continue

    all_events.sort(key=lambda e: e.date, reverse=True)
    return all_events


def _strip_html(text: str) -> str:
    """Remove HTML tags, convert block elements to newlines."""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "\n  - ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_mod.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@async_ttl_cache(1800)
async def fetch_fed_article(url: str) -> str:
    """Fetch and extract article text from a Federal Reserve press release page."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=15, follow_redirects=True)
        resp.raise_for_status()

    text = resp.text

    marker = "col-xs-12 col-sm-8 col-md-8"

    # Collect all content column divs (heading + body + attachments)
    chunks: list[str] = []
    pos = 0
    while True:
        idx = text.find(marker, pos)
        if idx < 0:
            break
        div_start = text.rfind("<div", max(0, idx - 200), idx)
        if div_start < 0:
            div_start = idx
        chunks.append(text[div_start : div_start + 10000])
        pos = idx + len(marker)

    if not chunks:
        return ""

    combined = "\n".join(chunks)

    # Strip out share buttons, release time, and attachment panels
    combined = re.sub(r'<li[^>]*class="share[^"]*"[^>]*>.*?</ul>', "", combined, flags=re.DOTALL)
    combined = re.sub(r'<p[^>]*class="releaseTime"[^>]*>.*?(?:</p>|<ul[^>]*>)', "", combined, flags=re.DOTALL)
    combined = re.sub(r'<div[^>]*class="[^"]*panel-attachments[^"]*"[^>]*>.*', "", combined, flags=re.DOTALL)

    # Cut off at footer/nav boilerplate
    for stop in ["Last Update:", "Board of Governors of the Federal Reserve System",
                  "Media Contacts:", "For media inquiries"]:
        stop_idx = combined.find(stop)
        if stop_idx > 0:
            combined = combined[:stop_idx]
            break

    # Remove remaining empty share list items
    combined = re.sub(r'<li[^>]*class=\'shareDL__item\'[^>]*>.*?</li>', "", combined, flags=re.DOTALL)
    combined = re.sub(r'<ul[^>]*class="[^"]*shareDL[^"]*"[^>]*>.*?</ul>', "", combined, flags=re.DOTALL)

    result = _strip_html(combined)
    # Strip trailing whitespace per line, collapse blank lines
    lines = [line.strip() for line in result.splitlines()]
    # Remove empty list marker lines
    lines = [l for l in lines if l != "-"]
    result = "\n".join(lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    # Trim trailing boilerplate that survived HTML stripping
    for stop in ["Media Contacts:", "For media inquiries", "Last Update:"]:
        stop_idx = result.find(stop)
        if stop_idx > 0:
            result = result[:stop_idx]
            break
    return result.strip()

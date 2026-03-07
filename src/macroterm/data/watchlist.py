from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from macroterm.logger import get_logger

logger = get_logger("watchlist")

WATCHLIST_PATH = Path.home() / ".config" / "macroterm" / "watchlist.json"


@dataclass
class WatchlistEntry:
    series_id: str
    source: str
    display_name: str
    date_added: str


def load() -> list[WatchlistEntry]:
    try:
        data = json.loads(WATCHLIST_PATH.read_text())
        entries = [WatchlistEntry(**e) for e in data]
        logger.debug("loaded watchlist", extra={"extra_fields": {
            "count": len(entries), "path": str(WATCHLIST_PATH),
        }})
        return entries
    except (FileNotFoundError, json.JSONDecodeError, TypeError, KeyError):
        logger.debug("no watchlist found or invalid format", extra={"extra_fields": {
            "path": str(WATCHLIST_PATH),
        }})
        return []


def save(entries: list[WatchlistEntry]) -> None:
    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    WATCHLIST_PATH.write_text(json.dumps([asdict(e) for e in entries], indent=2))


def add(series_id: str, source: str, display_name: str) -> None:
    entries = load()
    if any(e.series_id == series_id and e.source == source for e in entries):
        logger.debug("series already in watchlist", extra={"extra_fields": {
            "series_id": series_id, "source": source,
        }})
        return
    entries.append(WatchlistEntry(
        series_id=series_id,
        source=source,
        display_name=display_name,
        date_added=datetime.now().isoformat(),
    ))
    save(entries)
    logger.info("added to watchlist", extra={"extra_fields": {
        "series_id": series_id, "source": source, "total": len(entries),
    }})


def remove(series_id: str, source: str) -> None:
    entries = load()
    entries = [e for e in entries if not (e.series_id == series_id and e.source == source)]
    save(entries)
    logger.info("removed from watchlist", extra={"extra_fields": {
        "series_id": series_id, "source": source, "total": len(entries),
    }})


def is_bookmarked(series_id: str, source: str) -> bool:
    return any(e.series_id == series_id and e.source == source for e in load())

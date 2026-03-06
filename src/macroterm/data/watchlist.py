from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

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
        return [WatchlistEntry(**e) for e in data]
    except (FileNotFoundError, json.JSONDecodeError, TypeError, KeyError):
        return []


def save(entries: list[WatchlistEntry]) -> None:
    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    WATCHLIST_PATH.write_text(json.dumps([asdict(e) for e in entries], indent=2))


def add(series_id: str, source: str, display_name: str) -> None:
    entries = load()
    if any(e.series_id == series_id and e.source == source for e in entries):
        return
    entries.append(WatchlistEntry(
        series_id=series_id,
        source=source,
        display_name=display_name,
        date_added=datetime.now().isoformat(),
    ))
    save(entries)


def remove(series_id: str, source: str) -> None:
    entries = load()
    entries = [e for e in entries if not (e.series_id == series_id and e.source == source)]
    save(entries)


def is_bookmarked(series_id: str, source: str) -> bool:
    return any(e.series_id == series_id and e.source == source for e in load())

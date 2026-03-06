from __future__ import annotations

import asyncio
from dataclasses import dataclass

from macroterm.data.bls import search_catalog
from macroterm.data.fred import search_series


@dataclass
class SearchResult:
    source: str
    series_id: str
    title: str
    frequency: str
    units: str
    last_updated: str


async def search_all(query: str, limit: int = 25) -> list[SearchResult]:
    results: list[SearchResult] = []

    # BLS catalog search is synchronous/instant — run it first
    for entry in search_catalog(query, limit=limit):
        results.append(SearchResult(
            source="BLS",
            series_id=entry.series_id,
            title=entry.title,
            frequency=entry.frequency,
            units=entry.units,
            last_updated="",
        ))

    # FRED search hits the network — run async
    try:
        fred_results = await search_series(query, limit=limit)
        for s in fred_results:
            results.append(SearchResult(
                source="FRED",
                series_id=s.id,
                title=s.title,
                frequency=s.frequency,
                units=s.units,
                last_updated=s.last_updated,
            ))
    except Exception:
        pass  # FRED failure shouldn't block BLS results

    return results

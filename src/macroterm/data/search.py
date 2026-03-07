from __future__ import annotations

from dataclasses import dataclass

from macroterm.data.bls import search_catalog
from macroterm.data.fred import search_series
from macroterm.logger import get_logger

logger = get_logger("search")


@dataclass
class SearchResult:
    source: str
    series_id: str
    title: str
    frequency: str
    units: str
    last_updated: str


async def search_all(
    query: str, limit: int = 25, tag_names: str | None = None,
) -> list[SearchResult]:
    logger.debug("searching all sources", extra={"extra_fields": {
        "query": query, "limit": limit, "tag_names": tag_names,
    }})
    results: list[SearchResult] = []

    # BLS catalog search is synchronous/instant — run it first
    # BLS is US-only national data, so skip when a non-US geo filter is active
    geo_tags = (tag_names or "").split(";") if tag_names else []
    skip_bls = any(
        t in ("state", "msa", "county") for t in geo_tags
    ) or (geo_tags and "usa" not in geo_tags and "nation" not in geo_tags)
    if not skip_bls:
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
        fred_results = await search_series(query, limit=limit, tag_names=tag_names)
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
        logger.warning("FRED search failed, returning BLS results only", extra={"extra_fields": {
            "query": query,
        }}, exc_info=True)

    logger.info("search completed", extra={"extra_fields": {
        "query": query, "count": len(results),
    }})
    return results

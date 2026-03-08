from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta

import httpx

from macroterm.data.cache import async_ttl_cache
from macroterm.logger import get_logger

logger = get_logger("fred")

FRED_BASE_URL = "https://api.stlouisfed.org/fred"


def _api_key() -> str:
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
        logger.error("FRED_API_KEY not set")
        raise RuntimeError(
            "FRED_API_KEY environment variable is not set. "
            "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    return key


@dataclass
class Series:
    id: str
    title: str
    frequency: str
    units: str
    last_updated: str


@dataclass
class Observation:
    date: str
    value: str


@dataclass
class Release:
    id: int
    name: str
    link: str


@dataclass
class ReleaseDate:
    release_id: int
    release_name: str
    date: str


GEO_TYPES: dict[str, str] = {
    "National": "nation",
    "US State": "state",
    "US Metro (MSA)": "msa",
    "US County": "county",
}

GEO_COUNTRIES: dict[str, str] = {
    "United States": "usa",
    "Japan": "japan",
    "Germany": "germany",
    "United Kingdom": "united kingdom",
    "Canada": "canada",
    "France": "france",
    "China": "china",
    "Australia": "australia",
    "Brazil": "brazil",
    "India": "india",
    "Mexico": "mexico",
    "South Korea": "korea",
    "Italy": "italy",
    "Spain": "spain",
    "Netherlands": "netherlands",
    "Switzerland": "switzerland",
    "Sweden": "sweden",
    "Norway": "norway",
    "Denmark": "denmark",
    "South Africa": "south africa",
    "Russia": "russia",
    "Turkey": "turkey",
    "Indonesia": "indonesia",
    "Euro Area": "europe",
    "World": "world",
}

GEO_US_STATES: dict[str, str] = {
    "Alabama": "al",
    "Alaska": "ak",
    "Arizona": "az",
    "Arkansas": "ar",
    "California": "ca",
    "Colorado": "co",
    "Connecticut": "ct",
    "Delaware": "de",
    "District of Columbia": "dc",
    "Florida": "fl",
    "Georgia": "ga",
    "Hawaii": "hi",
    "Idaho": "id",
    "Illinois": "il",
    "Indiana": "in",
    "Iowa": "ia",
    "Kansas": "ks",
    "Kentucky": "ky",
    "Louisiana": "la",
    "Maine": "me",
    "Maryland": "md",
    "Massachusetts": "ma",
    "Michigan": "mi",
    "Minnesota": "mn",
    "Mississippi": "ms",
    "Missouri": "mo",
    "Montana": "mt",
    "Nebraska": "ne",
    "Nevada": "nv",
    "New Hampshire": "nh",
    "New Jersey": "nj",
    "New Mexico": "nm",
    "New York": "ny",
    "North Carolina": "nc",
    "North Dakota": "nd",
    "Ohio": "oh",
    "Oklahoma": "ok",
    "Oregon": "or",
    "Pennsylvania": "pa",
    "Rhode Island": "ri",
    "South Carolina": "sc",
    "South Dakota": "sd",
    "Tennessee": "tn",
    "Texas": "tx",
    "Utah": "ut",
    "Vermont": "vt",
    "Virginia": "va",
    "Washington": "wa",
    "West Virginia": "wv",
    "Wisconsin": "wi",
    "Wyoming": "wy",
}

GEO_US_METROS: dict[str, str] = {
    "New York": "new york",
    "Los Angeles": "los angeles",
    "Chicago": "chicago",
    "Dallas-Fort Worth": "dallas",
    "Houston": "houston",
    "Washington DC": "washington",
    "Miami": "miami",
    "Philadelphia": "philadelphia",
    "Atlanta": "atlanta",
    "Boston": "boston",
    "Phoenix": "phoenix",
    "San Francisco": "san francisco",
    "Seattle": "seattle",
    "Minneapolis": "minneapolis",
    "Denver": "denver",
    "San Diego": "san diego",
    "Tampa": "tampa",
    "Detroit": "detroit",
    "Portland": "portland",
    "Charlotte": "charlotte",
    "Austin": "austin",
    "Nashville": "nashville",
    "Las Vegas": "las vegas",
    "Baltimore": "baltimore",
    "St. Louis": "st. louis",
}

GEO_US_COUNTIES: dict[str, str] = {
    "Los Angeles County, CA": "los angeles",
    "Cook County, IL": "cook",
    "Harris County, TX": "harris",
    "Maricopa County, AZ": "maricopa",
    "San Diego County, CA": "san diego",
    "Orange County, CA": "orange",
    "Miami-Dade County, FL": "miami-dade",
    "Dallas County, TX": "dallas",
    "King County, WA": "king",
    "Clark County, NV": "clark",
    "Tarrant County, TX": "tarrant",
    "San Bernardino County, CA": "san bernardino",
    "Bexar County, TX": "bexar",
    "Broward County, FL": "broward",
    "Wayne County, MI": "wayne",
    "Allegheny County, PA": "allegheny",
    "New York County, NY": "new york",
    "Middlesex County, MA": "middlesex",
    "Sacramento County, CA": "sacramento",
    "Palm Beach County, FL": "palm beach",
}

CATEGORIES: dict[str, int] = {
    # Prices
    "Consumer Price Indexes": 9,
    "Producer Price Indexes": 31,
    "Commodities": 32217,
    "House Price Indexes": 32261,
    # Employment & Labor
    "Employment & Labor": 10,
    "Weekly Initial Claims": 32240,
    "ADP Employment": 32250,
    # National Accounts & Debt
    "National Accounts (GDP)": 32992,
    "Federal Government Debt": 5,
    # Production & Business
    "Industrial Production": 3,
    "Retail Trade": 6,
    "Manufacturing": 32429,
    "Construction": 32436,
    "Housing": 97,
    "Business Surveys": 33936,
    # Money & Finance
    "Money Supply (M1 & M2)": 29,
    "Monetary Base & Reserves": 124,
    "Financial Indicators": 46,
    "Exchange Rates (Daily)": 94,
    "Trade & Balance of Payments": 125,
    # Other
    "Recession Probabilities": 33120,
}


@async_ttl_cache(3600)
async def get_category_series(
    category_id: int, limit: int = 100, tag_names: str | None = None,
) -> list[Series]:
    params: dict = {
        "api_key": _api_key(),
        "file_type": "json",
        "category_id": category_id,
        "limit": limit,
        "order_by": "popularity",
        "sort_order": "desc",
    }
    if tag_names:
        params["tag_names"] = tag_names
    logger.debug("fetching category series", extra={"extra_fields": {
        "category_id": category_id, "limit": limit, "tag_names": tag_names,
    }})
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{FRED_BASE_URL}/category/series",
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

    results = [
        Series(
            id=s["id"],
            title=s["title"],
            frequency=s.get("frequency", ""),
            units=s.get("units", ""),
            last_updated=s.get("last_updated", ""),
        )
        for s in data.get("seriess", [])
    ]
    logger.info("category series fetched", extra={"extra_fields": {
        "category_id": category_id, "count": len(results),
    }})
    return results


@async_ttl_cache(300)
async def search_series(
    query: str, limit: int = 25, tag_names: str | None = None,
) -> list[Series]:
    params: dict = {
        "api_key": _api_key(),
        "file_type": "json",
        "search_text": query,
        "limit": limit,
    }
    if tag_names:
        params["tag_names"] = tag_names
    logger.debug("searching FRED series", extra={"extra_fields": {
        "query": query, "limit": limit, "tag_names": tag_names,
    }})
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{FRED_BASE_URL}/series/search",
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

    results = [
        Series(
            id=s["id"],
            title=s["title"],
            frequency=s.get("frequency", ""),
            units=s.get("units", ""),
            last_updated=s.get("last_updated", ""),
        )
        for s in data.get("seriess", [])
    ]
    logger.info("FRED search completed", extra={"extra_fields": {
        "query": query, "count": len(results),
    }})
    return results


@async_ttl_cache(600)
async def get_observations(series_id: str, limit: int = 10) -> list[Observation]:
    logger.debug("fetching observations", extra={"extra_fields": {
        "series_id": series_id, "limit": limit,
    }})
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{FRED_BASE_URL}/series/observations",
            params={
                "api_key": _api_key(),
                "file_type": "json",
                "series_id": series_id,
                "sort_order": "desc",
                "limit": limit,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    results = [
        Observation(date=o["date"], value=o["value"])
        for o in data.get("observations", [])
    ]
    logger.info("observations fetched", extra={"extra_fields": {
        "series_id": series_id, "count": len(results),
    }})
    return results


@async_ttl_cache(3600)
async def get_releases(limit: int = 50) -> list[Release]:
    logger.debug("fetching releases", extra={"extra_fields": {"limit": limit}})
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{FRED_BASE_URL}/releases",
            params={
                "api_key": _api_key(),
                "file_type": "json",
                "limit": limit,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    results = [
        Release(
            id=r["id"],
            name=r["name"],
            link=r.get("link", ""),
        )
        for r in data.get("releases", [])
    ]
    logger.info("releases fetched", extra={"extra_fields": {"count": len(results)}})
    return results


@async_ttl_cache(3600)
async def get_release_dates(
    start: date | None = None,
    end: date | None = None,
    limit: int = 100,
) -> list[ReleaseDate]:
    if start is None:
        start = date.today()
    if end is None:
        end = start + timedelta(days=14)

    logger.debug("fetching release dates", extra={"extra_fields": {
        "start": start.isoformat(), "end": end.isoformat(), "limit": limit,
    }})
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{FRED_BASE_URL}/releases/dates",
            params={
                "api_key": _api_key(),
                "file_type": "json",
                "realtime_start": start.isoformat(),
                "realtime_end": end.isoformat(),
                "include_release_dates_with_no_data": "true",
                "limit": limit,
                "sort_order": "asc",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    results = [
        ReleaseDate(
            release_id=r["release_id"],
            release_name=r.get("release_name", ""),
            date=r["date"],
        )
        for r in data.get("release_dates", [])
    ]
    logger.info("release dates fetched", extra={"extra_fields": {
        "start": start.isoformat(), "end": end.isoformat(), "count": len(results),
    }})
    return results

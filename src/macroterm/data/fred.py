from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta

import httpx

from macroterm.data.cache import async_ttl_cache

FRED_BASE_URL = "https://api.stlouisfed.org/fred"


def _api_key() -> str:
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
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
async def get_category_series(category_id: int, limit: int = 25) -> list[Series]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FRED_BASE_URL}/category/series",
            params={
                "api_key": _api_key(),
                "file_type": "json",
                "category_id": category_id,
                "limit": limit,
                "order_by": "popularity",
                "sort_order": "desc",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return [
        Series(
            id=s["id"],
            title=s["title"],
            frequency=s.get("frequency", ""),
            units=s.get("units", ""),
            last_updated=s.get("last_updated", ""),
        )
        for s in data.get("seriess", [])
    ]


@async_ttl_cache(300)
async def search_series(query: str, limit: int = 25) -> list[Series]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FRED_BASE_URL}/series/search",
            params={
                "api_key": _api_key(),
                "file_type": "json",
                "search_text": query,
                "limit": limit,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return [
        Series(
            id=s["id"],
            title=s["title"],
            frequency=s.get("frequency", ""),
            units=s.get("units", ""),
            last_updated=s.get("last_updated", ""),
        )
        for s in data.get("seriess", [])
    ]


@async_ttl_cache(600)
async def get_observations(series_id: str, limit: int = 10) -> list[Observation]:
    async with httpx.AsyncClient() as client:
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

    return [
        Observation(date=o["date"], value=o["value"])
        for o in data.get("observations", [])
    ]


@async_ttl_cache(3600)
async def get_releases(limit: int = 50) -> list[Release]:
    async with httpx.AsyncClient() as client:
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

    return [
        Release(
            id=r["id"],
            name=r["name"],
            link=r.get("link", ""),
        )
        for r in data.get("releases", [])
    ]


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

    async with httpx.AsyncClient() as client:
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

    return [
        ReleaseDate(
            release_id=r["release_id"],
            release_name=r.get("release_name", ""),
            date=r["date"],
        )
        for r in data.get("release_dates", [])
    ]

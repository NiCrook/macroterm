from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta

import httpx

from macroterm.data.cache import async_ttl_cache

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


def _api_key() -> str:
    key = os.environ.get("FINNHUB_API_KEY", "")
    if not key:
        raise RuntimeError(
            "FINNHUB_API_KEY environment variable is not set. "
            "Get a free key at https://finnhub.io/register"
        )
    return key


@dataclass
class EconomicEvent:
    country: str
    event: str
    time: str
    actual: str
    estimate: str
    prev: str
    unit: str
    impact: str


@async_ttl_cache(1800)
async def get_economic_calendar(
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[EconomicEvent]:
    if from_date is None:
        from_date = date.today()
    if to_date is None:
        to_date = from_date + timedelta(days=14)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FINNHUB_BASE_URL}/calendar/economic",
            params={
                "token": _api_key(),
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
            },
        )
        resp.raise_for_status()
        data = resp.json()

    events = []
    for e in data.get("economicCalendar", []):
        events.append(
            EconomicEvent(
                country=e.get("country", ""),
                event=e.get("event", ""),
                time=e.get("time", ""),
                actual=_fmt_value(e.get("actual")),
                estimate=_fmt_value(e.get("estimate")),
                prev=_fmt_value(e.get("prev")),
                unit=e.get("unit", ""),
                impact=e.get("impact", ""),
            )
        )
    return events


@async_ttl_cache(1800)
async def get_upcoming_releases(days: int = 14) -> list[EconomicEvent]:
    today = date.today()
    events = await get_economic_calendar(today, today + timedelta(days=days))
    return [e for e in events if e.actual == "—"]


@async_ttl_cache(1800)
async def get_recent_releases(days: int = 7) -> list[EconomicEvent]:
    today = date.today()
    events = await get_economic_calendar(today - timedelta(days=days), today)
    return [e for e in events if e.actual != "—"]


def _fmt_value(val: object) -> str:
    if val is None:
        return "—"
    return str(val)

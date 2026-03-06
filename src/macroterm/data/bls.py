from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from macroterm.data.cache import async_ttl_cache

BLS_BASE_URL = "https://api.bls.gov/publicAPI/v2"


def _api_key() -> str | None:
    return os.environ.get("BLS_API_KEY")


@dataclass
class BLSSeries:
    series_id: str
    year: str
    period: str
    value: str
    period_name: str


@async_ttl_cache(1800)
async def get_series_data(
    series_ids: list[str],
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict[str, list[BLSSeries]]:
    payload: dict = {"seriesid": series_ids}
    key = _api_key()
    if key:
        payload["registrationkey"] = key
    if start_year:
        payload["startyear"] = str(start_year)
    if end_year:
        payload["endyear"] = str(end_year)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BLS_BASE_URL}/timeseries/data/",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    results: dict[str, list[BLSSeries]] = {}
    for series in data.get("Results", {}).get("series", []):
        sid = series["seriesID"]
        results[sid] = [
            BLSSeries(
                series_id=sid,
                year=d["year"],
                period=d["period"],
                value=d["value"],
                period_name=d.get("periodName", ""),
            )
            for d in series.get("data", [])
        ]
    return results


# Common BLS series IDs for reference
COMMON_SERIES = {
    "CPI-U (All Urban)": "CUUR0000SA0",
    "CPI-U (Core)": "CUUR0000SA0L1E",
    "Unemployment Rate": "LNS14000000",
    "Nonfarm Payrolls": "CES0000000001",
    "Average Hourly Earnings": "CES0500000003",
    "PPI (Final Demand)": "WPUFD49104",
}

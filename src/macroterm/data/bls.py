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


@dataclass
class BLSCatalogEntry:
    series_id: str
    title: str
    category: str
    frequency: str
    units: str
    keywords: str


CATALOG: list[BLSCatalogEntry] = [
    # Prices: CPI
    BLSCatalogEntry("CUUR0000SA0", "CPI-U All Items (All Urban Consumers)", "Prices: CPI", "Monthly", "Index", "cpi inflation consumer prices"),
    BLSCatalogEntry("CUUR0000SA0L1E", "CPI-U Core (Less Food and Energy)", "Prices: CPI", "Monthly", "Index", "cpi core inflation consumer prices"),
    BLSCatalogEntry("CUUR0000SAF1", "CPI-U Food", "Prices: CPI", "Monthly", "Index", "cpi food prices inflation"),
    BLSCatalogEntry("CUUR0000SETA01", "CPI-U New Vehicles", "Prices: CPI", "Monthly", "Index", "cpi cars vehicles prices"),
    BLSCatalogEntry("CUUR0000SEHA", "CPI-U Rent of Primary Residence", "Prices: CPI", "Monthly", "Index", "cpi rent housing shelter"),
    BLSCatalogEntry("CUUR0000SAM", "CPI-U Medical Care", "Prices: CPI", "Monthly", "Index", "cpi medical healthcare prices"),
    BLSCatalogEntry("CUUR0000SETB01", "CPI-U Gasoline", "Prices: CPI", "Monthly", "Index", "cpi gas gasoline energy fuel"),
    BLSCatalogEntry("CUUR0000SEHE01", "CPI-U Owners Equivalent Rent", "Prices: CPI", "Monthly", "Index", "cpi oer rent housing shelter"),
    # Prices: PPI
    BLSCatalogEntry("WPUFD49104", "PPI Final Demand", "Prices: PPI", "Monthly", "Index", "ppi producer prices inflation"),
    BLSCatalogEntry("WPUFD4131", "PPI Final Demand Less Food and Energy", "Prices: PPI", "Monthly", "Index", "ppi core producer prices inflation"),
    BLSCatalogEntry("WPUFD41", "PPI Final Demand Goods", "Prices: PPI", "Monthly", "Index", "ppi producer prices goods"),
    BLSCatalogEntry("WPUFD42", "PPI Final Demand Services", "Prices: PPI", "Monthly", "Index", "ppi producer prices services"),
    # Prices: Import/Export
    BLSCatalogEntry("EIUIR", "Import Price Index (All Imports)", "Prices: Trade", "Monthly", "Index", "import prices trade"),
    BLSCatalogEntry("EIUIQ", "Export Price Index (All Exports)", "Prices: Trade", "Monthly", "Index", "export prices trade"),
    # Employment
    BLSCatalogEntry("LNS14000000", "Unemployment Rate", "Employment", "Monthly", "Percent", "unemployment jobs labor"),
    BLSCatalogEntry("LNS11000000", "Civilian Labor Force Level", "Employment", "Monthly", "Thousands", "labor force participation"),
    BLSCatalogEntry("LNS11300000", "Labor Force Participation Rate", "Employment", "Monthly", "Percent", "labor force participation lfpr"),
    BLSCatalogEntry("LNS13000000", "Employment Level", "Employment", "Monthly", "Thousands", "employment jobs"),
    BLSCatalogEntry("LNS14000006", "Unemployment Rate - Black or African American", "Employment", "Monthly", "Percent", "unemployment race black"),
    BLSCatalogEntry("LNS14000009", "Unemployment Rate - Hispanic or Latino", "Employment", "Monthly", "Percent", "unemployment race hispanic"),
    BLSCatalogEntry("LNS13008636", "Number Unemployed 27 Weeks and Over", "Employment", "Monthly", "Thousands", "long-term unemployment"),
    BLSCatalogEntry("LNS12032194", "Multiple Jobholders", "Employment", "Monthly", "Thousands", "multiple jobs employment"),
    # Payrolls
    BLSCatalogEntry("CES0000000001", "Total Nonfarm Payrolls", "Payrolls", "Monthly", "Thousands", "nonfarm payrolls jobs employment nfp"),
    BLSCatalogEntry("CES1000000001", "Mining and Logging Payrolls", "Payrolls", "Monthly", "Thousands", "mining logging jobs payrolls"),
    BLSCatalogEntry("CES2000000001", "Construction Payrolls", "Payrolls", "Monthly", "Thousands", "construction jobs payrolls"),
    BLSCatalogEntry("CES3000000001", "Manufacturing Payrolls", "Payrolls", "Monthly", "Thousands", "manufacturing jobs payrolls"),
    BLSCatalogEntry("CES4200000001", "Retail Trade Payrolls", "Payrolls", "Monthly", "Thousands", "retail trade jobs payrolls"),
    BLSCatalogEntry("CES6500000001", "Education and Health Services Payrolls", "Payrolls", "Monthly", "Thousands", "education health jobs payrolls"),
    BLSCatalogEntry("CES7000000001", "Leisure and Hospitality Payrolls", "Payrolls", "Monthly", "Thousands", "leisure hospitality jobs payrolls"),
    BLSCatalogEntry("CES9000000001", "Government Payrolls", "Payrolls", "Monthly", "Thousands", "government public sector jobs payrolls"),
    # Wages & Costs
    BLSCatalogEntry("CES0500000003", "Average Hourly Earnings (Private)", "Wages & Costs", "Monthly", "Dollars", "wages earnings hourly pay"),
    BLSCatalogEntry("CES0500000002", "Average Weekly Hours (Private)", "Wages & Costs", "Monthly", "Hours", "hours worked weekly"),
    BLSCatalogEntry("CES0500000008", "Average Weekly Earnings (Private)", "Wages & Costs", "Monthly", "Dollars", "wages earnings weekly pay"),
    BLSCatalogEntry("CIU1010000000000A", "Employment Cost Index - Total Compensation", "Wages & Costs", "Quarterly", "Index", "eci employment cost compensation wages"),
    BLSCatalogEntry("CIU2010000000000A", "Employment Cost Index - Wages and Salaries", "Wages & Costs", "Quarterly", "Index", "eci wages salaries"),
    BLSCatalogEntry("PRS85006112", "Nonfarm Business Unit Labor Costs", "Wages & Costs", "Quarterly", "Index", "unit labor costs wages"),
    # JOLTS
    BLSCatalogEntry("JTS000000000000000JOL", "JOLTS Job Openings", "JOLTS", "Monthly", "Thousands", "jolts job openings vacancies"),
    BLSCatalogEntry("JTS000000000000000HIL", "JOLTS Hires", "JOLTS", "Monthly", "Thousands", "jolts hires hiring"),
    BLSCatalogEntry("JTS000000000000000TSL", "JOLTS Total Separations", "JOLTS", "Monthly", "Thousands", "jolts separations turnover"),
    BLSCatalogEntry("JTS000000000000000QUL", "JOLTS Quits", "JOLTS", "Monthly", "Thousands", "jolts quits quit rate"),
    # Productivity
    BLSCatalogEntry("PRS85006092", "Nonfarm Business Labor Productivity", "Productivity", "Quarterly", "Index", "productivity output labor"),
]


def get_categories() -> list[str]:
    seen: dict[str, None] = {}
    for entry in CATALOG:
        seen.setdefault(entry.category, None)
    return list(seen)


def get_by_category(category: str) -> list[BLSCatalogEntry]:
    return [e for e in CATALOG if e.category == category]


def search_catalog(query: str, limit: int = 25) -> list[BLSCatalogEntry]:
    terms = query.lower().split()
    scored: list[tuple[int, BLSCatalogEntry]] = []
    for entry in CATALOG:
        searchable = f"{entry.title} {entry.keywords} {entry.series_id}".lower()
        score = sum(1 for t in terms if t in searchable)
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:limit]]

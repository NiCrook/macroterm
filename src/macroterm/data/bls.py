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
    BLSCatalogEntry("CUUR0000SAF11", "CPI-U Food at Home", "Prices: CPI", "Monthly", "Index", "cpi food groceries prices"),
    BLSCatalogEntry("CUUR0000SEFV", "CPI-U Food Away from Home", "Prices: CPI", "Monthly", "Index", "cpi food restaurants dining"),
    BLSCatalogEntry("CUUR0000SETA01", "CPI-U New Vehicles", "Prices: CPI", "Monthly", "Index", "cpi cars vehicles prices"),
    BLSCatalogEntry("CUUR0000SETA02", "CPI-U Used Cars and Trucks", "Prices: CPI", "Monthly", "Index", "cpi used cars vehicles prices"),
    BLSCatalogEntry("CUUR0000SEHA", "CPI-U Rent of Primary Residence", "Prices: CPI", "Monthly", "Index", "cpi rent housing shelter"),
    BLSCatalogEntry("CUUR0000SEHE01", "CPI-U Owners Equivalent Rent", "Prices: CPI", "Monthly", "Index", "cpi oer rent housing shelter"),
    BLSCatalogEntry("CUUR0000SAH1", "CPI-U Shelter", "Prices: CPI", "Monthly", "Index", "cpi shelter housing"),
    BLSCatalogEntry("CUUR0000SAM", "CPI-U Medical Care", "Prices: CPI", "Monthly", "Index", "cpi medical healthcare prices"),
    BLSCatalogEntry("CUUR0000SAE1", "CPI-U Education", "Prices: CPI", "Monthly", "Index", "cpi education tuition prices"),
    BLSCatalogEntry("CUUR0000SAA", "CPI-U Apparel", "Prices: CPI", "Monthly", "Index", "cpi apparel clothing prices"),
    BLSCatalogEntry("CUUR0000SAR", "CPI-U Recreation", "Prices: CPI", "Monthly", "Index", "cpi recreation entertainment prices"),
    BLSCatalogEntry("CUUR0000SETB01", "CPI-U Gasoline", "Prices: CPI", "Monthly", "Index", "cpi gas gasoline energy fuel"),
    BLSCatalogEntry("CUUR0000SEHF01", "CPI-U Electricity", "Prices: CPI", "Monthly", "Index", "cpi electricity energy utilities"),
    BLSCatalogEntry("CUUR0000SEHF02", "CPI-U Utility Gas Service", "Prices: CPI", "Monthly", "Index", "cpi natural gas energy utilities"),
    BLSCatalogEntry("CUUR0000SA0E", "CPI-U Energy", "Prices: CPI", "Monthly", "Index", "cpi energy prices oil gas"),
    # Prices: PPI
    BLSCatalogEntry("WPUFD49104", "PPI Final Demand", "Prices: PPI", "Monthly", "Index", "ppi producer prices inflation"),
    BLSCatalogEntry("WPUFD4131", "PPI Final Demand Less Food and Energy", "Prices: PPI", "Monthly", "Index", "ppi core producer prices inflation"),
    BLSCatalogEntry("WPUFD41", "PPI Final Demand Goods", "Prices: PPI", "Monthly", "Index", "ppi producer prices goods"),
    BLSCatalogEntry("WPUFD42", "PPI Final Demand Services", "Prices: PPI", "Monthly", "Index", "ppi producer prices services"),
    # Prices: Import/Export
    BLSCatalogEntry("EIUIR", "Import Price Index (All Imports)", "Prices: Trade", "Monthly", "Index", "import prices trade"),
    BLSCatalogEntry("EIUIQ", "Export Price Index (All Exports)", "Prices: Trade", "Monthly", "Index", "export prices trade"),
    # Employment
    BLSCatalogEntry("LNS14000000", "Unemployment Rate (U-3)", "Employment", "Monthly", "Percent", "unemployment jobs labor u3"),
    BLSCatalogEntry("LNS13327709", "Unemployment Rate (U-6)", "Employment", "Monthly", "Percent", "unemployment underemployment u6 broad"),
    BLSCatalogEntry("LNS11000000", "Civilian Labor Force Level", "Employment", "Monthly", "Thousands", "labor force participation"),
    BLSCatalogEntry("LNS11300000", "Labor Force Participation Rate", "Employment", "Monthly", "Percent", "labor force participation lfpr"),
    BLSCatalogEntry("LNS13000000", "Employment Level", "Employment", "Monthly", "Thousands", "employment jobs"),
    BLSCatalogEntry("LNS12600000", "Employment-Population Ratio", "Employment", "Monthly", "Percent", "employment population ratio epop"),
    BLSCatalogEntry("LNS14000006", "Unemployment Rate - Black or African American", "Employment", "Monthly", "Percent", "unemployment race black"),
    BLSCatalogEntry("LNS14000009", "Unemployment Rate - Hispanic or Latino", "Employment", "Monthly", "Percent", "unemployment race hispanic"),
    BLSCatalogEntry("LNS14000003", "Unemployment Rate - Women", "Employment", "Monthly", "Percent", "unemployment women gender"),
    BLSCatalogEntry("LNS13008636", "Number Unemployed 27 Weeks and Over", "Employment", "Monthly", "Thousands", "long-term unemployment"),
    BLSCatalogEntry("LNS12032194", "Multiple Jobholders", "Employment", "Monthly", "Thousands", "multiple jobs employment"),
    BLSCatalogEntry("LNS12032195", "Part-Time for Economic Reasons", "Employment", "Monthly", "Thousands", "part-time involuntary underemployment"),
    BLSCatalogEntry("LNS15026645", "Discouraged Workers", "Employment", "Monthly", "Thousands", "discouraged workers marginally attached"),
    # Payrolls
    BLSCatalogEntry("CES0000000001", "Total Nonfarm Payrolls", "Payrolls", "Monthly", "Thousands", "nonfarm payrolls jobs employment nfp"),
    BLSCatalogEntry("CES0500000001", "Total Private Payrolls", "Payrolls", "Monthly", "Thousands", "private payrolls jobs employment"),
    BLSCatalogEntry("CES1000000001", "Mining and Logging Payrolls", "Payrolls", "Monthly", "Thousands", "mining logging jobs payrolls"),
    BLSCatalogEntry("CES2000000001", "Construction Payrolls", "Payrolls", "Monthly", "Thousands", "construction jobs payrolls"),
    BLSCatalogEntry("CES3000000001", "Manufacturing Payrolls", "Payrolls", "Monthly", "Thousands", "manufacturing jobs payrolls"),
    BLSCatalogEntry("CES4200000001", "Retail Trade Payrolls", "Payrolls", "Monthly", "Thousands", "retail trade jobs payrolls"),
    BLSCatalogEntry("CES4300000001", "Transportation and Warehousing Payrolls", "Payrolls", "Monthly", "Thousands", "transportation warehousing logistics jobs payrolls"),
    BLSCatalogEntry("CES5000000001", "Information Payrolls", "Payrolls", "Monthly", "Thousands", "information tech media jobs payrolls"),
    BLSCatalogEntry("CES5500000001", "Financial Activities Payrolls", "Payrolls", "Monthly", "Thousands", "finance insurance real estate jobs payrolls"),
    BLSCatalogEntry("CES6000000001", "Professional and Business Services Payrolls", "Payrolls", "Monthly", "Thousands", "professional business services jobs payrolls"),
    BLSCatalogEntry("CES6500000001", "Education and Health Services Payrolls", "Payrolls", "Monthly", "Thousands", "education health jobs payrolls"),
    BLSCatalogEntry("CES7000000001", "Leisure and Hospitality Payrolls", "Payrolls", "Monthly", "Thousands", "leisure hospitality jobs payrolls"),
    BLSCatalogEntry("CES9000000001", "Government Payrolls", "Payrolls", "Monthly", "Thousands", "government public sector jobs payrolls"),
    # Wages & Costs
    BLSCatalogEntry("CES0500000003", "Average Hourly Earnings (Private)", "Wages & Costs", "Monthly", "Dollars", "wages earnings hourly pay"),
    BLSCatalogEntry("CES0500000002", "Average Weekly Hours (Private)", "Wages & Costs", "Monthly", "Hours", "hours worked weekly"),
    BLSCatalogEntry("CES0500000008", "Average Weekly Earnings (Private)", "Wages & Costs", "Monthly", "Dollars", "wages earnings weekly pay"),
    BLSCatalogEntry("CES0500000011", "Average Hourly Earnings (Production Workers)", "Wages & Costs", "Monthly", "Dollars", "wages earnings hourly production nonsupervisory"),
    BLSCatalogEntry("CIU1010000000000A", "Employment Cost Index - Total Compensation", "Wages & Costs", "Quarterly", "Index", "eci employment cost compensation wages"),
    BLSCatalogEntry("CIU2010000000000A", "Employment Cost Index - Wages and Salaries", "Wages & Costs", "Quarterly", "Index", "eci wages salaries"),
    BLSCatalogEntry("CIU3010000000000A", "Employment Cost Index - Benefits", "Wages & Costs", "Quarterly", "Index", "eci benefits compensation"),
    BLSCatalogEntry("PRS85006112", "Nonfarm Business Unit Labor Costs", "Wages & Costs", "Quarterly", "Index", "unit labor costs wages"),
    # JOLTS
    BLSCatalogEntry("JTS000000000000000JOL", "JOLTS Job Openings", "JOLTS", "Monthly", "Thousands", "jolts job openings vacancies"),
    BLSCatalogEntry("JTS000000000000000HIL", "JOLTS Hires", "JOLTS", "Monthly", "Thousands", "jolts hires hiring"),
    BLSCatalogEntry("JTS000000000000000TSL", "JOLTS Total Separations", "JOLTS", "Monthly", "Thousands", "jolts separations turnover"),
    BLSCatalogEntry("JTS000000000000000QUL", "JOLTS Quits", "JOLTS", "Monthly", "Thousands", "jolts quits quit rate"),
    BLSCatalogEntry("JTS000000000000000LDL", "JOLTS Layoffs and Discharges", "JOLTS", "Monthly", "Thousands", "jolts layoffs discharges fired"),
    # Productivity
    BLSCatalogEntry("PRS85006092", "Nonfarm Business Labor Productivity", "Productivity", "Quarterly", "Index", "productivity output labor"),
    BLSCatalogEntry("PRS85006152", "Nonfarm Business Real Compensation Per Hour", "Productivity", "Quarterly", "Index", "real compensation wages productivity"),
    BLSCatalogEntry("PRS30006092", "Manufacturing Labor Productivity", "Productivity", "Quarterly", "Index", "manufacturing productivity output"),
    # Work Stoppages
    BLSCatalogEntry("WSU00100000000000001", "Work Stoppages - Number of Stoppages", "Work Stoppages", "Annual", "Count", "strikes lockouts work stoppages labor disputes"),
    BLSCatalogEntry("WSU00100000000000002", "Work Stoppages - Workers Involved", "Work Stoppages", "Annual", "Thousands", "strikes lockouts workers involved labor disputes"),
    BLSCatalogEntry("WSU00100000000000003", "Work Stoppages - Days Idle", "Work Stoppages", "Annual", "Thousands", "strikes lockouts days idle lost labor disputes"),
    # Consumer Expenditure
    BLSCatalogEntry("CXUTOTALEXPLB0101M", "Total Average Annual Expenditures", "Consumer Expenditure", "Annual", "Dollars", "consumer expenditure spending household"),
    BLSCatalogEntry("CXUFOODEXPLB0101M", "Food Expenditures", "Consumer Expenditure", "Annual", "Dollars", "consumer expenditure food spending household"),
    BLSCatalogEntry("CXUHOUSINGEXPLB0101M", "Housing Expenditures", "Consumer Expenditure", "Annual", "Dollars", "consumer expenditure housing rent mortgage spending"),
    BLSCatalogEntry("CXUTRANSEXPLB0101M", "Transportation Expenditures", "Consumer Expenditure", "Annual", "Dollars", "consumer expenditure transportation cars spending"),
    BLSCatalogEntry("CXUHEALTHEXPLB0101M", "Healthcare Expenditures", "Consumer Expenditure", "Annual", "Dollars", "consumer expenditure healthcare medical spending"),
    BLSCatalogEntry("CXUENTRTNEXPLB0101M", "Entertainment Expenditures", "Consumer Expenditure", "Annual", "Dollars", "consumer expenditure entertainment recreation spending"),
    BLSCatalogEntry("CXUAPPARELEXPLB0101M", "Apparel Expenditures", "Consumer Expenditure", "Annual", "Dollars", "consumer expenditure apparel clothing spending"),
    BLSCatalogEntry("CXUEDUCAEXPLB0101M", "Education Expenditures", "Consumer Expenditure", "Annual", "Dollars", "consumer expenditure education tuition spending"),
    # Occupational Employment & Wages
    BLSCatalogEntry("OEUM000000000000000000001", "All Occupations - Employment", "Occupational Wages", "Annual", "Count", "occupational employment total jobs"),
    BLSCatalogEntry("OEUM000000000000000000004", "All Occupations - Mean Hourly Wage", "Occupational Wages", "Annual", "Dollars", "occupational wages hourly mean average"),
    BLSCatalogEntry("OEUM000000000000000000013", "All Occupations - Annual Mean Wage", "Occupational Wages", "Annual", "Dollars", "occupational wages annual mean average salary"),
    BLSCatalogEntry("OEUM00000011000000000000004", "Management - Mean Hourly Wage", "Occupational Wages", "Annual", "Dollars", "management executive wages hourly"),
    BLSCatalogEntry("OEUM00000015000000000000004", "Computer & Mathematical - Mean Hourly Wage", "Occupational Wages", "Annual", "Dollars", "computer technology software wages hourly"),
    BLSCatalogEntry("OEUM00000029000000000000004", "Healthcare Practitioners - Mean Hourly Wage", "Occupational Wages", "Annual", "Dollars", "healthcare medical practitioners wages hourly"),
    BLSCatalogEntry("OEUM00000041000000000000004", "Sales - Mean Hourly Wage", "Occupational Wages", "Annual", "Dollars", "sales retail wages hourly"),
    BLSCatalogEntry("OEUM00000047000000000000004", "Construction & Extraction - Mean Hourly Wage", "Occupational Wages", "Annual", "Dollars", "construction extraction trades wages hourly"),
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

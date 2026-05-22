"""Direct REST API client for TMS alarm data.

Replaces Playwright per-page scraping with a single HTTP call using
isPaginated=false, returning all records in one round-trip.
COMF and IOF are fetched in parallel via ThreadPoolExecutor.
"""

from __future__ import annotations
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed

_ALARM_CODES = ["COMF", "IOF"]


def fetch_all_alarms(
    api_base: str,
    token: str,
    ctx_headers: dict[str, str],
    base_params: list[tuple[str, str]],
    origin: str = "https://tms.surbana.tech",
    alarm_codes: list[str] | None = None,
) -> dict[str, list[dict]]:
    """
    Fetch alarm records for each alarm code in parallel.
    Returns {alarm_code: [raw_record, ...]} for each requested code.

    Using isPaginated=false means the server returns every matching row
    in a single response — no pagination loop, no per-page waits.
    """
    if alarm_codes is None:
        alarm_codes = _ALARM_CODES

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/plain, */*",
        "Origin": origin,
        **ctx_headers,
    }

    results: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=len(alarm_codes)) as pool:
        futures = {
            pool.submit(_fetch_one, api_base, headers, base_params, code): code
            for code in alarm_codes
        }
        for fut in as_completed(futures):
            code = futures[fut]
            results[code] = fut.result()
            print(f"  {code}: {len(results[code])} raw records")

    return results


def _fetch_one(
    api_base: str,
    headers: dict[str, str],
    base_params: list[tuple[str, str]],
    alarm_code: str,
) -> list[dict]:
    """Single API call for one alarm code; returns the data[] array."""
    params: list[tuple[str, str]] = [
        *base_params,
        ("assetType",     "lmd"),
        ("pageNumber",    "1"),
        ("pageSize",      "9999"),
        ("searchText",    ""),
        ("totalItems",    "0"),
        ("totalPages",    "0"),
        ("totalFilter",   "0"),
        ("isPaginated",   "false"),
        ("isActive",      "true"),
        ("selectedAlarmCodes", alarm_code),
    ]

    with httpx.Client(verify=False, timeout=30) as client:
        resp = client.get(api_base, params=params, headers=headers)
        resp.raise_for_status()
        payload = resp.json()
        rows = payload.get("data", [])
        if rows:
            print(f"  [{alarm_code}] API field keys: {sorted(rows[0].keys())}")
        return rows

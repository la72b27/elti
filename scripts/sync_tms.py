"""Sync TMS alarm data to the ELTI Cloudflare Worker.

Optimization vs. the previous Playwright-only approach:
  Old: full browser pagination (~2.5 min — multiple pages × per-page waits × 2 codes)
  New: browser login only → intercept one API request → direct HTTP with
       isPaginated=false + parallel COMF/IOF fetch (~25–30 s total)
"""

from __future__ import annotations
import os
import re
import json
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed

from .tms_auth import login_and_capture
from .tms_api import fetch_all_alarms
from .tms_transform import normalize_records, merge_records, build_payload


def _get_env_url(key: str) -> str:
    val = os.environ.get(key, "").strip().strip("`\"'")
    url = val.rstrip("/")
    if url and not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


TMS_BASE_URL      = _get_env_url("TMS_BASE_URL")
TMS_USERNAME      = os.environ.get("TMS_USERNAME", "")
TMS_PASSWORD      = os.environ.get("TMS_PASSWORD", "")
ELTI_WORKER_URL   = _get_env_url("ELTI_WORKER_URL")
ELTI_UPDATE_TOKEN = os.environ.get("ELTI_UPDATE_TOKEN", "")
ONEMAP_EMAIL      = os.environ.get("ONEMAP_EMAIL", "")
ONEMAP_PASSWORD   = os.environ.get("ONEMAP_PASSWORD", "")

_ONEMAP_TOKEN_URL  = "https://www.onemap.gov.sg/api/auth/post/getToken"
_ONEMAP_SEARCH_URL = "https://www.onemap.gov.sg/api/common/elastic/search"


# ── OneMap postcode helpers ────────────────────────────────────────────────────

def _fetch_onemap_token() -> str:
    if not ONEMAP_EMAIL or not ONEMAP_PASSWORD:
        return ""
    try:
        r = httpx.post(
            _ONEMAP_TOKEN_URL,
            json={"email": ONEMAP_EMAIL, "password": ONEMAP_PASSWORD},
            timeout=20,
        )
        r.raise_for_status()
        return r.json().get("access_token", "")
    except Exception as e:
        print(f"  [onemap] token error: {e}")
        return ""


def _choose_postal(results: list[dict], blk: str, street: str) -> str:
    """Pick the best postal code from OneMap search results (mirrors onemap_api.py)."""
    best_score, best_post = -1, ""
    ub = (blk or "").upper().strip()
    us = (street or "").upper().strip()
    for item in results:
        postal = str(item.get("POSTAL", "")).strip()
        if not postal or postal == "NIL":
            continue
        b  = str(item.get("BLK_NO",    "")).upper().strip()
        rd = str(item.get("ROAD_NAME", "")).upper().strip()
        score = 100 + (10 if ub and b == ub else 0)
        if us and rd:
            score += 20 if rd == us else (10 if us in rd or rd in us else 0)
        if score > best_score:
            best_score, best_post = score, postal
    return best_post


def _enrich_postcodes(records: list[dict]) -> None:
    """Add Postcode field to each record in-place via OneMap API."""
    token = _fetch_onemap_token()
    if not token:
        print("  [postcode] ONEMAP_EMAIL/PASSWORD not set — Postcode will be empty")
        for r in records:
            r.setdefault("Postcode", "")
        return

    # Deduplicate (Block, Address) pairs
    addr_cache: dict[tuple, str] = {
        (r.get("Block", ""), r.get("Address", "")): "" for r in records
    }

    def _query(key: tuple) -> tuple[tuple, str]:
        blk, street = key
        b = re.sub(r"\b(?:BLK|BLOCK)\b", " ", blk or "", flags=re.IGNORECASE)
        q = re.sub(r"\s+", " ", f"{b} {street}".strip()).upper()
        if not q:
            return key, ""
        try:
            resp = httpx.get(
                _ONEMAP_SEARCH_URL,
                params={"searchVal": q, "returnGeom": "N",
                        "getAddrDetails": "Y", "pageNum": 1},
                headers={"Authorization": token},
                timeout=12,
                verify=False,
            )
            if resp.status_code == 401:
                return key, ""
            resp.raise_for_status()
            return key, _choose_postal(resp.json().get("results", []), blk, street)
        except Exception:
            return key, ""

    n = len(addr_cache)
    print(f"  [postcode] looking up {n} unique addresses...")
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_query, k): k for k in addr_cache}
        for future in as_completed(futures):
            k, postal = future.result()
            addr_cache[k] = postal

    found = sum(1 for v in addr_cache.values() if v)
    print(f"  [postcode] found {found}/{n}")

    for r in records:
        r["Postcode"] = addr_cache.get((r.get("Block", ""), r.get("Address", "")), "")


# ── Worker push ────────────────────────────────────────────────────────────────

def _push_to_worker(payload: dict) -> None:
    headers = {"Content-Type": "application/json"}
    if ELTI_UPDATE_TOKEN:
        headers["X-Update-Token"] = ELTI_UPDATE_TOKEN
    with httpx.Client() as client:
        resp = client.post(
            f"{ELTI_WORKER_URL}/update",
            content=json.dumps(payload),
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        print(f"Pushed {len(payload['records'])} records → HTTP {resp.status_code}")


def main() -> None:
    if not TMS_BASE_URL:
        print("ERROR: TMS_BASE_URL is empty.")
        return
    if not ELTI_WORKER_URL:
        print("ERROR: ELTI_WORKER_URL is empty.")
        return

    print(f"TMS_BASE_URL:    {TMS_BASE_URL}")
    print(f"ELTI_WORKER_URL: {ELTI_WORKER_URL}")

    # ── 1. Browser login → capture bearer token + context headers ──────────────
    print("\n[1/5] Browser login & token capture...")
    captured = login_and_capture(TMS_BASE_URL, TMS_USERNAME, TMS_PASSWORD)

    # ── 2. Parallel direct API calls (isPaginated=false, no page loops) ────────
    print("\n[2/5] Fetching all alarms via REST API (COMF + IOF in parallel)...")
    raw_by_code = fetch_all_alarms(
        api_base=captured["api_base"],
        token=captured["token"],
        ctx_headers=captured["ctx_headers"],
        base_params=captured["base_params"],
        origin=captured.get("origin", "https://tms.surbana.tech"),
    )

    # ── 3. Filter EP1WM → normalize → merge Lift letters ──────────────────────
    print("\n[3/5] Filtering EP1WM, normalizing, merging...")
    normalized = normalize_records(raw_by_code)
    print(f"  EP1WM records : {len(normalized)}")
    merged = merge_records(normalized)
    print(f"  After merge   : {len(merged)}")

    # ── 4. Enrich with postcodes via OneMap ────────────────────────────────────
    print("\n[4/5] Looking up postcodes via OneMap...")
    _enrich_postcodes(merged)

    payload = build_payload(merged)
    print(f"  comf={payload['comf_count']}  iof={payload['iof_count']}")

    # ── 5. Push to Cloudflare Worker ───────────────────────────────────────────
    print("\n[5/5] Pushing to Cloudflare Worker...")
    _push_to_worker(payload)


if __name__ == "__main__":
    main()

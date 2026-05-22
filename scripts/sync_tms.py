"""Sync TMS alarm data to the ELTI Cloudflare Worker.

Optimization vs. the previous Playwright-only approach:
  Old: full browser pagination (~2.5 min — multiple pages × per-page waits × 2 codes)
  New: browser login only → intercept one API request → direct HTTP with
       isPaginated=false + parallel COMF/IOF fetch (~25–30 s total)
"""

from __future__ import annotations
import os
import json
import httpx

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
    print("\n[1/4] Browser login & token capture...")
    captured = login_and_capture(TMS_BASE_URL, TMS_USERNAME, TMS_PASSWORD)

    # ── 2. Parallel direct API calls (isPaginated=false, no page loops) ────────
    print("\n[2/4] Fetching all alarms via REST API (COMF + IOF in parallel)...")
    raw_by_code = fetch_all_alarms(
        api_base=captured["api_base"],
        token=captured["token"],
        ctx_headers=captured["ctx_headers"],
        base_params=captured["base_params"],
        origin=captured.get("origin", "https://tms.surbana.tech"),
    )

    # ── 3. Filter EP1WM → normalize → merge Lift letters ──────────────────────
    print("\n[3/4] Filtering EP1WM, normalizing, merging...")
    normalized = normalize_records(raw_by_code)
    print(f"  EP1WM records : {len(normalized)}")
    merged = merge_records(normalized)
    print(f"  After merge   : {len(merged)}")

    payload = build_payload(merged)
    print(f"  comf={payload['comf_count']}  iof={payload['iof_count']}")

    # ── 4. Push to Cloudflare Worker ───────────────────────────────────────────
    print("\n[4/4] Pushing to Cloudflare Worker...")
    _push_to_worker(payload)


if __name__ == "__main__":
    main()

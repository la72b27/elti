"""Upload LSS MasterList IP data to ELTI Worker (masterlist_lss table).

Reads LSS - MasterList.xlsx, groups by postal_code, picks the row whose
"IP Address" starts with "10.5." as the master row (all hardware versions),
and POSTs to /api/lss/upload in batches of 200.

Rule: if a postal_code has multiple rows, only the one with a 10.5.x.x
IP Address is used as the primary (lmd_ip / proxy_ip / vp_tun_ip /
lmd_tun_ip). Non-10.5 IPs are ignored for primary fields.
DVR IPs are still aggregated across all lifts in the group.

Usage:
    set ELTI_WORKER_URL=https://elti.insg.vip
    set ELTI_UPDATE_TOKEN=<token>
    python -m scripts.upload_lss
"""

from __future__ import annotations
import os
import json
import httpx
import pandas as pd
from ipaddress import IPv4Address

ELTI_WORKER_URL   = os.environ.get("ELTI_WORKER_URL", "https://elti.insg.vip").strip().rstrip("/")
ELTI_UPDATE_TOKEN = os.environ.get("ELTI_UPDATE_TOKEN", "")
XLSX_PATH         = os.environ.get("XLSX_PATH",
                       r"D:\TempStudy\VibeCoding\LS\LSS - MasterList.xlsx")
BATCH_SIZE = 200


def _ip_plus_one(ip_str: str) -> str:
    s = (ip_str or "").strip()
    if not s:
        return ""
    try:
        return str(IPv4Address(int(IPv4Address(s)) + 1))
    except Exception:
        return ""


def _clean_ip(val) -> str:
    s = str(val).strip() if val is not None and str(val).strip() not in ("nan", "") else ""
    return "" if s in ("", "0.0.0.0", "nan", "NaN") else s


def build_records(df: pd.DataFrame) -> list[dict]:
    """Build one LSS record per postal_code.

    Primary row = first row (sorted by Lift) whose IP Address starts with
    '10.5.' — regardless of hardware version.  Non-10.5 rows are only used
    for DVR IP aggregation.
    """
    work = df.copy()

    # Normalise postal_code to 6-digit string
    work["postal_code"] = (
        work["postal_code"]
        .fillna(0).astype(float).astype(int).astype(str)
    )
    work = work[work["postal_code"] != "0"]

    # Tag rows that have a 10.5.x.x IP Address
    work["_is_105"] = (
        work["IP Address"]
        .fillna("").astype(str).str.strip()
        .str.startswith("10.5.")
    )

    records: list[dict] = []
    for postal_code, group in work.groupby("postal_code"):
        group = group.sort_values("Lift")

        # Primary: first 10.5.x.x row; fall back to first row if none
        primary_rows = group[group["_is_105"]]
        primary = primary_rows.iloc[0] if len(primary_rows) else group.iloc[0]

        lmd_ip     = _clean_ip(primary.get("IP Address"))
        proxy_ip   = _clean_ip(primary.get("Host2"))
        vp_tun_ip  = _clean_ip(primary.get("Gateway1"))
        lmd_tun_ip = _ip_plus_one(vp_tun_ip) if vp_tun_ip else ""

        # DVR IP: aggregate across all lifts with non-empty dvrIP convert
        dvr_parts: list[str] = []
        for _, row in group.iterrows():
            dvr  = _clean_ip(row.get("dvrIP convert"))
            lift = str(row.get("Lift", "")).strip()
            if dvr and lift:
                dvr_parts.append(f"{lift}={dvr}")
        dvr_ip = ", ".join(dvr_parts)

        records.append({
            "postal_code": postal_code,
            "lmd_ip":      lmd_ip,
            "proxy_ip":    proxy_ip,
            "vp_tun_ip":   vp_tun_ip,
            "lmd_tun_ip":  lmd_tun_ip,
            "dvr_ip":      dvr_ip,
        })

    return records


def main() -> None:
    if not ELTI_UPDATE_TOKEN:
        print("ERROR: ELTI_UPDATE_TOKEN is not set.")
        return

    print(f"Reading: {XLSX_PATH}")
    df = pd.read_excel(XLSX_PATH)
    records = build_records(df)
    total_105 = int(df["IP Address"].fillna("").astype(str).str.startswith("10.5.").sum())
    print(f"Built {len(records)} records from {total_105} rows with 10.5.x.x IPs "
          f"(across all hardware versions, {len(df)} total rows)")

    headers: dict = {
        "Content-Type":   "application/json",
        "X-Update-Token": ELTI_UPDATE_TOKEN,
    }

    total = 0
    with httpx.Client(timeout=60) as client:
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i : i + BATCH_SIZE]
            resp = client.post(
                f"{ELTI_WORKER_URL}/api/lss/upload",
                content=json.dumps({"records": batch}),
                headers=headers,
            )
            resp.raise_for_status()
            upserted = resp.json().get("upserted", len(batch))
            total += upserted
            print(f"  Batch {i // BATCH_SIZE + 1}/{-(-len(records) // BATCH_SIZE)}: "
                  f"{upserted} upserted (cumulative {total}/{len(records)})")

    print(f"Done — total upserted: {total}")


if __name__ == "__main__":
    main()

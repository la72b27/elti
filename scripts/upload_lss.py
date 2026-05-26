"""One-time enrichment script: upload LSS MasterList IP data to ELTI Worker.

Reads LSS - MasterList.xlsx, filters to EP1WM rows, groups by postal_code,
and POSTs to /api/lss/upload in batches of 200.

Usage:
    ELTI_WORKER_URL=https://elti.insg.vip \
    ELTI_UPDATE_TOKEN=<token> \
    XLSX_PATH="D:/TempStudy/VibeCoding/LS/LSS - MasterList.xlsx" \
    python -m scripts.upload_lss
"""

from __future__ import annotations
import os
import json
import httpx
import pandas as pd
from ipaddress import IPv4Address

ELTI_WORKER_URL   = os.environ.get("ELTI_WORKER_URL", "").strip().rstrip("/")
ELTI_UPDATE_TOKEN = os.environ.get("ELTI_UPDATE_TOKEN", "")
XLSX_PATH         = os.environ.get("XLSX_PATH",
                       r"D:\TempStudy\VibeCoding\LS\LSS - MasterList.xlsx")
BATCH_SIZE = 200


def _ip_plus_one(ip_str: str) -> str:
    """Return IP address incremented by 1, or '' on error."""
    s = (ip_str or "").strip().lstrip("-")
    if not s:
        return ""
    try:
        return str(IPv4Address(int(IPv4Address(s)) + 1))
    except Exception:
        return ""


def _clean_ip(val) -> str:
    """Convert pandas cell to clean IP string, return '' for NaN/0.0.0.0."""
    s = str(val).strip() if val is not None and str(val).strip() != "nan" else ""
    return "" if s in ("", "0.0.0.0", "nan", "NaN") else s


def build_records(df: pd.DataFrame) -> list[dict]:
    """Aggregate EP1WM rows by postal_code into one record per block."""
    ep1wm = df[df["lmd_hardware_version"] == "EP1WM"].copy()

    # Normalise postal_code: float 670101.0 → str "670101"
    ep1wm["postal_code"] = (
        ep1wm["postal_code"]
        .fillna(0)
        .astype(float)
        .astype(int)
        .astype(str)
    )

    records: list[dict] = []
    for postal_code, group in ep1wm.groupby("postal_code"):
        if postal_code == "0":
            continue
        group = group.sort_values("Lift")

        # Primary row (first by Lift letter — usually A, the EP1WM master)
        primary = group.iloc[0]

        lmd_ip    = _clean_ip(primary.get("IP Address"))
        proxy_ip  = _clean_ip(primary.get("Host2"))
        vp_tun_ip = _clean_ip(primary.get("Gateway1"))
        lmd_tun_ip = _ip_plus_one(vp_tun_ip) if vp_tun_ip else ""

        # DVR IP: aggregate across all EP1WM lifts — format "A=x, B=y"
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
    if not ELTI_WORKER_URL:
        print("ERROR: ELTI_WORKER_URL is not set.")
        return

    print(f"Reading: {XLSX_PATH}")
    df = pd.read_excel(XLSX_PATH)
    records = build_records(df)
    print(f"Built {len(records)} records from {len(df[df['lmd_hardware_version']=='EP1WM'])} EP1WM rows")

    headers: dict = {"Content-Type": "application/json"}
    if ELTI_UPDATE_TOKEN:
        headers["X-Update-Token"] = ELTI_UPDATE_TOKEN

    total = 0
    with httpx.Client(timeout=30) as client:
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i : i + BATCH_SIZE]
            resp = client.post(
                f"{ELTI_WORKER_URL}/api/lss/upload",
                content=json.dumps({"records": batch}),
                headers=headers,
            )
            resp.raise_for_status()
            result = resp.json()
            upserted = result.get("upserted", len(batch))
            total += upserted
            print(f"  Batch {i // BATCH_SIZE + 1}: upserted {upserted}")

    print(f"Done — total upserted: {total}")


if __name__ == "__main__":
    main()

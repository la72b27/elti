"""Transform raw TMS API records into the ELTI worker payload format."""

from __future__ import annotations
import re
from datetime import datetime, timezone, timedelta
from itertools import groupby

SGT = timezone(timedelta(hours=8))

# bitsDescription values that map to a known RBE display code
BITS_TO_RBE: dict[str, str] = {
    "Communication Failure":        "COMF",
    "I/O Serial Comm Cable Faulty": "IOF",
}


# ── public API ─────────────────────────────────────────────────────────────────

def normalize_records(
    raw_by_code: dict[str, list[dict]],
) -> list[dict]:
    """
    Filter to EP1WM hardware only and convert API field names to internal names.

    raw_by_code: {alarm_code: [raw_record, ...]}  from tms_api.fetch_all_alarms()
    Returns a flat list of normalized dicts.
    """
    out: list[dict] = []
    for alarm_code, records in raw_by_code.items():
        for raw in records:
            rec = _normalize_one(raw, alarm_code)
            if rec is not None:
                out.append(rec)
    return out


def merge_records(records: list[dict]) -> list[dict]:
    """Group by (TC_Display, Pfx, Block) and concatenate Lift letters."""
    if not records:
        return []
    key_fn = lambda r: (r.get("TC_Display", ""), r.get("Pfx", ""), r.get("Block", ""))
    sorted_recs = sorted(records, key=key_fn)
    merged: list[dict] = []
    for _key, group_iter in groupby(sorted_recs, key=key_fn):
        group = list(group_iter)
        base = dict(group[0])
        lifts = sorted({str(r.get("Lift", "")) for r in group if r.get("Lift", "")})
        base["Lift"] = "".join(lifts)
        merged.append(base)
    return merged


def build_payload(records: list[dict]) -> dict:
    """Produce the JSON payload expected by the ELTI Cloudflare Worker /update endpoint."""
    comf_out = [r for r in records if r["RBE"] == "COMF"]
    iof_out  = [r for r in records if r["RBE"] == "IOF"]

    tc_stats: dict[str, dict[str, int]] = {"COMF": {}, "IOF": {}}
    for r in comf_out:
        tc = r["TC_Display"]
        tc_stats["COMF"][tc] = tc_stats["COMF"].get(tc, 0) + 1
    for r in iof_out:
        tc = r["TC_Display"]
        tc_stats["IOF"][tc] = tc_stats["IOF"].get(tc, 0) + 1

    payload_records: list[dict] = []
    for r in comf_out + iof_out:
        rbe = r.get("RBE_Display", r.get("RBE", "COMF"))
        payload_records.append({
            "TC_Display":  r.get("TC_Display", "-"),
            "Pfx":         r.get("Pfx", ""),
            "Block":       r.get("Block", ""),
            "Lift":        r.get("Lift", ""),
            "Address":     r.get("Address", ""),
            "LCOY":        r.get("LCOY", ""),
            "Status Date": r.get("Status Date", "-"),
            "RBE":         rbe,
            "RBE_Display": rbe,
            "Status":      r.get("Status", "SET"),
        })

    return {
        "records":      payload_records,
        "comf_count":   len(comf_out),
        "iof_count":    len(iof_out),
        "tc_stats":     tc_stats,
        "last_updated": datetime.now(SGT).strftime("%Y-%m-%d %H:%M"),
    }


# ── internals ──────────────────────────────────────────────────────────────────

def _normalize_one(raw: dict, alarm_code: str) -> dict | None:
    """Return None if hardware version is not EP1WM."""
    if raw.get("hardwareVersion", "") != "EP1WM":
        return None

    bits_desc = raw.get("bitsDescription", "")
    rbe_display = BITS_TO_RBE.get(bits_desc, alarm_code)

    return {
        "TC_Display":       raw.get("townCouncil", "-"),
        "Pfx":              raw.get("prefix", ""),
        "Block":            raw.get("block", ""),
        "Lift":             raw.get("liftLetter", ""),
        "Address":          raw.get("street", ""),
        "Hardware Version": raw.get("hardwareVersion", ""),
        "LCOY":             raw.get("lcoy", raw.get("lcoYear", "")),
        "Status Date":      _parse_date(raw.get("setDate", "")),
        "Bits Description": bits_desc,
        "Status":           raw.get("status", "SET"),
        "RBE":              alarm_code,
        "RBE_Display":      rbe_display,
    }


def _parse_date(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return "-"
    # Pad single-digit hours/minutes: "14 May 2026 9:3" → "14 May 2026 09:03"
    m = re.match(r"^(.*?)\s+(\d{1,2}):(\d{1,2})$", raw)
    if m:
        return f"{m.group(1)} {m.group(2).zfill(2)}:{m.group(3).zfill(2)}"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.astimezone(SGT).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return raw

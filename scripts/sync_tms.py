import os
import json
import httpx
from datetime import datetime, timezone, timedelta

def get_env_url(key: str) -> str:
    val = os.environ.get(key, "").strip().strip("`\"'")
    print(f"DEBUG: Reading {key}, length: {len(val)}, value-prefix: {val[:10]!r}")
    url = val.rstrip("/")
    if url and not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url

TMS_BASE_URL = get_env_url("TMS_BASE_URL")
TMS_USERNAME = os.environ.get("TMS_USERNAME", "")
TMS_PASSWORD = os.environ.get("TMS_PASSWORD", "")
ELTI_WORKER_URL = get_env_url("ELTI_WORKER_URL")
ELTI_UPDATE_TOKEN = os.environ.get("ELTI_UPDATE_TOKEN", "")

TMS_AUTH_URL = "https://tms-production-api.azure.surbana.tech/auth/api/v1"
TMS_API_URL = "https://tms-production-api.azure.surbana.tech/portalapi"
TMS_LOGIN_URL = f"{TMS_AUTH_URL}/user"

SGT = timezone(timedelta(hours=8))

RBE_MAP = {"COMF": "COMF", "IOF": "IOF"}


def get_tms_token(client: httpx.Client) -> str:
    resp = client.post(
        TMS_LOGIN_URL,
        json={"username": TMS_USERNAME, "password": TMS_PASSWORD, "applicationId": "tms-public"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("accessToken") or data.get("token") or data.get("access_token", "")


def fetch_alarms(client: httpx.Client, token: str) -> list[dict]:
    resp = client.get(
        f"{TMS_API_URL}/tmsalarm/current-rbe-status",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def transform(raw_alarms: list[dict]) -> dict:
    records = []
    for alarm in raw_alarms:
        rbe_raw = str(alarm.get("rbe_type", "")).upper()
        rbe = rbe_raw if rbe_raw in RBE_MAP else "COMF"

        tc_raw = str(alarm.get("tc_code", ""))
        tc_display = tc_raw if tc_raw else "-"

        status_date_raw = alarm.get("status_date") or alarm.get("updated_at") or ""
        try:
            dt = datetime.fromisoformat(status_date_raw.replace("Z", "+00:00"))
            status_date = dt.astimezone(SGT).strftime("%Y-%m-%d %H:%M")
        except Exception:
            status_date = status_date_raw[:16] if status_date_raw else "-"

        records.append(
            {
                "TC_Display": tc_display,
                "Pfx": str(alarm.get("prefix", "")),
                "Block": str(alarm.get("block", "")),
                "Lift": str(alarm.get("lift", "")),
                "Address": str(alarm.get("address", "")),
                "LCOY": str(alarm.get("lcoy", "")),
                "Status Date": status_date,
                "RBE": rbe,
                "RBE_Display": rbe,
                "Status": str(alarm.get("status", "SET")),
            }
        )

    comf_records = [r for r in records if r["RBE"] == "COMF"]
    iof_records = [r for r in records if r["RBE"] == "IOF"]

    tc_stats: dict[str, dict[str, int]] = {"COMF": {}, "IOF": {}}
    for r in comf_records:
        tc = r["TC_Display"]
        tc_stats["COMF"][tc] = tc_stats["COMF"].get(tc, 0) + 1
    for r in iof_records:
        tc = r["TC_Display"]
        tc_stats["IOF"][tc] = tc_stats["IOF"].get(tc, 0) + 1

    now_sgt = datetime.now(SGT).strftime("%Y-%m-%d %H:%M")

    return {
        "records": records,
        "comf_count": len(comf_records),
        "iof_count": len(iof_records),
        "tc_stats": tc_stats,
        "last_updated": now_sgt,
    }


def push_to_worker(payload: dict) -> None:
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
        print(f"Pushed {len(payload['records'])} records → {resp.status_code}")


def main() -> None:
    if not TMS_BASE_URL:
        print("ERROR: TMS_BASE_URL is empty. Please check GitHub Secrets.")
        return
    if not ELTI_WORKER_URL:
        print("ERROR: ELTI_WORKER_URL is empty. Please check GitHub Secrets.")
        return

    with httpx.Client(verify=False) as client:
        token = get_tms_token(client)
        raw_alarms = fetch_alarms(client, token)

    payload = transform(raw_alarms)
    push_to_worker(payload)


if __name__ == "__main__":
    main()

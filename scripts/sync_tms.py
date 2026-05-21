import os
import json
import httpx
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

def get_env_url(key: str) -> str:
    val = os.environ.get(key, "").strip().strip("`\"'")
    url = val.rstrip("/")
    if url and not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url

TMS_BASE_URL = get_env_url("TMS_BASE_URL")
TMS_USERNAME = os.environ.get("TMS_USERNAME", "")
TMS_PASSWORD = os.environ.get("TMS_PASSWORD", "")
ELTI_WORKER_URL = get_env_url("ELTI_WORKER_URL")
ELTI_UPDATE_TOKEN = os.environ.get("ELTI_UPDATE_TOKEN", "")

TMS_API_BASE = "https://tms-production-api.azure.surbana.tech"

SGT = timezone(timedelta(hours=8))

RBE_MAP = {"COMF": "COMF", "IOF": "IOF"}

# 告警记录必须包含其中至少一个字段才算真实告警数据
ALARM_RECORD_KEYS = {
    "block", "Block", "blockNo", "block_no",
    "lift", "Lift", "liftNo", "lift_no", "liftId",
    "address", "Address", "fullAddress",
    "tc_code", "tcCode", "TC_Code",
    "rbe_type", "rbeType", "alarmStatus",
}


def _get_field(alarm: dict, *keys: str, default: str = "") -> str:
    """按优先级尝试多个字段名，兼容 snake_case 和 camelCase。"""
    for key in keys:
        val = alarm.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return default


def _extract_list(data) -> list[dict] | None:
    """从 API 响应中提取记录列表，支持多种包装结构。"""
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data
    if isinstance(data, dict):
        for key in ("data", "alarms", "items", "results", "records"):
            val = data.get(key)
            if isinstance(val, list) and val and isinstance(val[0], dict):
                return val
    return None


def login_and_capture(page) -> tuple[str | None, list[dict]]:
    """
    登录 TMS，捕获 token 和真实告警记录。
    返回 (token, alarm_records)，alarm_records 可能为空（需要 fallback）。
    """
    token = None
    alarm_records: list[dict] = []
    api_log: list[str] = []

    def handle_response(response):
        nonlocal token, alarm_records
        try:
            if TMS_API_BASE.replace("https://", "") not in response.url:
                return
            if response.status != 200:
                return

            data = response.json()
            short_url = response.url.split("?")[0]

            # 捕获 auth token
            if isinstance(data, dict):
                t = (data.get("accessToken") or data.get("token")
                     or data.get("access_token") or data.get("jwt"))
                if t and isinstance(t, str) and len(t) > 100:
                    print(f"  [token] {short_url} ({len(t)} chars)")
                    token = t

            # 记录所有含列表数据的 API 响应，用于诊断
            records = _extract_list(data)
            if records:
                first_keys = list(records[0].keys())
                api_log.append(
                    f"  [api]   {short_url} → {len(records)} records, "
                    f"keys: {first_keys}"
                )
                # 如果包含告警记录特征字段，认为是真实告警数据
                if ALARM_RECORD_KEYS & set(first_keys):
                    print(f"  [alarms] {short_url} → {len(records)} records, keys: {first_keys}")
                    alarm_records = records

        except Exception:
            pass

    page.on("response", handle_response)

    print(f"Navigating to login page: {TMS_BASE_URL}/login")
    page.goto(f"{TMS_BASE_URL}/login", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=15000)

    page.fill("#loginformemail", TMS_USERNAME)
    page.fill("#loginformpassword", TMS_PASSWORD)
    page.click('button[type="submit"]')

    # 等待 token 捕获，最多 15 秒
    for i in range(15):
        page.wait_for_timeout(1000)
        if token:
            print(f"  [token] Captured after ~{i + 1}s")
            break

    current_url = page.url
    print(f"Current URL after login: {current_url}")

    if not token:
        print("Token not yet captured, waiting extra 5s...")
        page.wait_for_timeout(5000)
        if not token and "login" in page.url.lower():
            raise RuntimeError("Login failed - check TMS_USERNAME and TMS_PASSWORD")

    # 等待主页 API 调用完成，捕获告警数据
    print("Waiting for main page to load alarm data...")
    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_timeout(5000)

    # 输出所有观察到的 API 端点，便于排查
    if api_log:
        print("\n--- All TMS API responses observed ---")
        for line in api_log:
            print(line)
        print("--------------------------------------\n")

    return token, alarm_records


def fetch_alarms_via_api(token: str) -> list[dict]:
    """
    当浏览器未能捕获告警记录时，用 token 直接调 API。
    尝试多个可能的端点。
    """
    endpoints = [
        f"{TMS_API_BASE}/portalapi/tmsalarm/getActiveAlarms",
        f"{TMS_API_BASE}/portalapi/tmsalarm/getAlarmRecords",
        f"{TMS_API_BASE}/portalapi/lmd/alarms",
        f"{TMS_API_BASE}/portalapi/tmsalarm/getAllTmsAlarmRecords",
    ]
    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(verify=False) as client:
        for url in endpoints:
            try:
                resp = client.get(url, params={"assetType": "LMD"}, headers=headers, timeout=15)
                print(f"  [api-try] {url} → {resp.status_code}")
                if resp.status_code != 200:
                    continue
                records = _extract_list(resp.json())
                if records and ALARM_RECORD_KEYS & set(records[0].keys()):
                    print(f"  [api-try] Found alarm records! keys: {list(records[0].keys())}")
                    return records
            except Exception as e:
                print(f"  [api-try] {url} → error: {e}")

    return []


def transform(raw_alarms: list[dict]) -> dict:
    records = []
    for alarm in raw_alarms:
        rbe_raw = _get_field(
            alarm,
            "rbe_type", "rbeType", "rbe", "alarmType", "alarm_type", "code",
            default=""
        ).upper()
        rbe = rbe_raw if rbe_raw in RBE_MAP else "COMF"

        tc_raw = _get_field(alarm, "tc_code", "tcCode", "TC_Code", "tc", default="")
        tc_display = tc_raw if tc_raw else "-"

        status_date_raw = (
            alarm.get("status_date") or alarm.get("statusDate")
            or alarm.get("updated_at") or alarm.get("updatedAt")
            or alarm.get("created_at") or alarm.get("createdAt")
            or ""
        )
        try:
            dt = datetime.fromisoformat(str(status_date_raw).replace("Z", "+00:00"))
            status_date = dt.astimezone(SGT).strftime("%Y-%m-%d %H:%M")
        except Exception:
            status_date = str(status_date_raw)[:16] if status_date_raw else "-"

        records.append(
            {
                "TC_Display":  tc_display,
                "Pfx":         _get_field(alarm, "prefix",  "Prefix",  "pfx"),
                "Block":       _get_field(alarm, "block",   "Block",   "blockNo",  "block_no"),
                "Lift":        _get_field(alarm, "lift",    "Lift",    "liftNo",   "lift_no",   "liftId", "lift_id"),
                "Address":     _get_field(alarm, "address", "Address", "fullAddress", "full_address"),
                "LCOY":        _get_field(alarm, "lcoy",    "LCOY",    "Lcoy"),
                "Status Date": status_date,
                "RBE":         rbe,
                "RBE_Display": rbe,
                "Status":      _get_field(alarm, "status", "Status", "alarmStatus", "alarm_status", default="SET"),
            }
        )

    comf_records = [r for r in records if r["RBE"] == "COMF"]
    iof_records  = [r for r in records if r["RBE"] == "IOF"]

    tc_stats: dict[str, dict[str, int]] = {"COMF": {}, "IOF": {}}
    for r in comf_records:
        tc = r["TC_Display"]
        tc_stats["COMF"][tc] = tc_stats["COMF"].get(tc, 0) + 1
    for r in iof_records:
        tc = r["TC_Display"]
        tc_stats["IOF"][tc] = tc_stats["IOF"].get(tc, 0) + 1

    return {
        "records":      records,
        "comf_count":   len(comf_records),
        "iof_count":    len(iof_records),
        "tc_stats":     tc_stats,
        "last_updated": datetime.now(SGT).strftime("%Y-%m-%d %H:%M"),
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
        print("ERROR: TMS_BASE_URL is empty.")
        return
    if not ELTI_WORKER_URL:
        print("ERROR: ELTI_WORKER_URL is empty.")
        return

    print(f"TMS_BASE_URL:    {TMS_BASE_URL}")
    print(f"ELTI_WORKER_URL: {ELTI_WORKER_URL}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        token, raw_alarms = login_and_capture(page)
        browser.close()

    if not token:
        raise RuntimeError("Could not capture auth token")
    print(f"Auth token captured ({len(token)} chars)")

    if raw_alarms:
        print(f"Alarm records captured from browser: {len(raw_alarms)}")
        print(f"Sample keys:          {list(raw_alarms[0].keys())}")
        print(f"Sample record:        {raw_alarms[0]}")
    else:
        print("No alarm records captured from browser, trying API endpoints directly...")
        raw_alarms = fetch_alarms_via_api(token)
        if raw_alarms:
            print(f"Alarm records from API fallback: {len(raw_alarms)}")
            print(f"Sample keys:   {list(raw_alarms[0].keys())}")
            print(f"Sample record: {raw_alarms[0]}")
        else:
            print("WARNING: No alarm records found from any source. Pushing empty payload.")

    payload = transform(raw_alarms)
    print(f"Transformed: comf_count={payload['comf_count']}, iof_count={payload['iof_count']}")
    push_to_worker(payload)


if __name__ == "__main__":
    main()

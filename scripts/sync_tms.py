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


def _get_field(alarm: dict, *keys: str, default: str = "") -> str:
    """从 alarm 字典中按优先级尝试多个字段名，兼容 snake_case 和 camelCase。"""
    for key in keys:
        val = alarm.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return default


def get_token_via_browser() -> str:
    token = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        def handle_response(response):
            nonlocal token
            try:
                url = response.url
                if TMS_API_BASE.replace("https://", "") not in url:
                    return
                if response.status != 200:
                    return
                data = response.json()
                if not isinstance(data, dict):
                    return
                t = (data.get("accessToken") or data.get("token")
                     or data.get("access_token") or data.get("jwt"))
                if t and isinstance(t, str) and len(t) > 100:
                    print(f"  [token] Captured from: {url.split('?')[0]} ({len(t)} chars)")
                    token = t
            except Exception:
                pass

        page.on("response", handle_response)

        print(f"Navigating to login page: {TMS_BASE_URL}/login")
        page.goto(f"{TMS_BASE_URL}/login", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)

        page.fill("#loginformemail", TMS_USERNAME)
        page.fill("#loginformpassword", TMS_PASSWORD)
        page.click('button[type="submit"]')

        # 逐秒轮询，捕获到 token 后提前退出，最多等 15 秒
        for i in range(15):
            page.wait_for_timeout(1000)
            if token:
                print(f"  [token] Captured after ~{i + 1}s")
                break

        current_url = page.url
        print(f"Current URL after login: {current_url}")

        # 已捕获到 token 说明 API 认证成功，无需依赖页面跳转
        if not token:
            # token 未捕获时再等 5 秒（应对页面跳转较慢的情况）
            print("Token not yet captured, waiting extra 5s for deferred auth response...")
            page.wait_for_timeout(5000)
            if not token and "login" in page.url.lower():
                raise RuntimeError("Login failed - check TMS_USERNAME and TMS_PASSWORD")

        browser.close()

    if not token:
        raise RuntimeError("Login succeeded but could not capture auth token from any API response")

    return token


def fetch_alarms(token: str) -> list[dict]:
    with httpx.Client(verify=False) as client:
        resp = client.get(
            f"{TMS_API_BASE}/portalapi/tmsalarm/getAllTmsAlarms",
            params={"assetType": "LMD"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        print(f"Alarms API response status: {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # 按常见 key 依次尝试
        for key in ("data", "alarms", "items", "results", "records"):
            if key in data and isinstance(data[key], list):
                return data[key]
        print(f"Unexpected response structure, top-level keys: {list(data.keys())}")
    return []


def transform(raw_alarms: list[dict]) -> dict:
    records = []
    for alarm in raw_alarms:
        # RBE 类型：同时兼容 snake_case / camelCase / 其他常见变体
        rbe_raw = _get_field(
            alarm,
            "rbe_type", "rbeType", "rbe", "alarmType", "alarm_type",
            default=""
        ).upper()
        rbe = rbe_raw if rbe_raw in RBE_MAP else "COMF"

        tc_raw = _get_field(alarm, "tc_code", "tcCode", "TC_Code", "tc", default="")
        tc_display = tc_raw if tc_raw else "-"

        # 时间字段：尝试多种命名
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
                "TC_Display": tc_display,
                "Pfx":        _get_field(alarm, "prefix",  "Prefix",  "pfx"),
                "Block":      _get_field(alarm, "block",   "Block",   "blockNo",  "block_no"),
                "Lift":       _get_field(alarm, "lift",    "Lift",    "liftNo",   "lift_no",   "liftId", "lift_id"),
                "Address":    _get_field(alarm, "address", "Address", "fullAddress", "full_address"),
                "LCOY":       _get_field(alarm, "lcoy",    "LCOY",    "Lcoy"),
                "Status Date": status_date,
                "RBE":        rbe,
                "RBE_Display": rbe,
                "Status":     _get_field(alarm, "status", "Status", "alarmStatus", "alarm_status", default="SET"),
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

    now_sgt = datetime.now(SGT).strftime("%Y-%m-%d %H:%M")

    return {
        "records":     records,
        "comf_count":  len(comf_records),
        "iof_count":   len(iof_records),
        "tc_stats":    tc_stats,
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

    print(f"TMS_BASE_URL:    {TMS_BASE_URL}")
    print(f"ELTI_WORKER_URL: {ELTI_WORKER_URL}")

    token = get_token_via_browser()
    print(f"Auth token captured ({len(token)} chars)")

    raw_alarms = fetch_alarms(token)
    print(f"Fetched {len(raw_alarms)} alarms from TMS")
    if raw_alarms:
        print(f"Sample alarm keys:          {list(raw_alarms[0].keys())}")
        print(f"Sample alarm (first record): {raw_alarms[0]}")

    payload = transform(raw_alarms)
    print(f"Transformed: comf_count={payload['comf_count']}, iof_count={payload['iof_count']}")
    push_to_worker(payload)


if __name__ == "__main__":
    main()

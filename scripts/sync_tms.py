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

TMS_BASE_URL  = get_env_url("TMS_BASE_URL")
TMS_USERNAME  = os.environ.get("TMS_USERNAME", "")
TMS_PASSWORD  = os.environ.get("TMS_PASSWORD", "")
ELTI_WORKER_URL   = get_env_url("ELTI_WORKER_URL")
ELTI_UPDATE_TOKEN = os.environ.get("ELTI_UPDATE_TOKEN", "")

TMS_API_BASE = "https://tms-production-api.azure.surbana.tech"
ALARM_PAGE   = "/lift/tms-lmd-alarm"

SGT    = timezone(timedelta(hours=8))
RBE_MAP = {"COMF": "COMF", "IOF": "IOF"}

# 硬件版本字段的候选名称
HW_VERSION_KEYS = (
    "hardwareVersion", "hardware_version", "hwVersion", "hw_version",
    "Hardware Version", "HardwareVersion", "firmware", "version",
)

# 真实告警记录特征字段（至少命中一个才算告警数据）
ALARM_RECORD_KEYS = {
    "block", "Block", "blockNo", "block_no",
    "lift",  "Lift",  "liftNo",  "lift_no", "liftId",
    "address", "Address", "fullAddress",
    "tc_code", "tcCode", "TC_Code",
    "rbe_type", "rbeType", "alarmStatus",
    "hardwareVersion", "hardware_version", "hwVersion",
}


def _get_field(d: dict, *keys: str, default: str = "") -> str:
    for k in keys:
        v = d.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return default


def _extract_list(data) -> list[dict] | None:
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data
    if isinstance(data, dict):
        for k in ("data", "alarms", "items", "results", "records", "content"):
            v = data.get(k)
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    return None


# ──────────────────────────────────────────────────────────
#  Browser automation
# ──────────────────────────────────────────────────────────

def _do_login(page) -> str:
    """登录 TMS，返回 access token（优先保留最长 token）。"""
    token = ""

    def on_resp(response):
        nonlocal token
        try:
            if TMS_API_BASE.replace("https://", "") not in response.url:
                return
            if response.status != 200:
                return
            data = response.json()
            if not isinstance(data, dict):
                return
            t = (data.get("accessToken") or data.get("token")
                 or data.get("access_token") or data.get("jwt") or "")
            if isinstance(t, str) and len(t) > 100 and len(t) > len(token):
                print(f"  [token] {response.url.split('?')[0]} ({len(t)} chars)")
                token = t
        except Exception:
            pass

    page.on("response", on_resp)

    print(f"  Navigating to login: {TMS_BASE_URL}/login")
    page.goto(f"{TMS_BASE_URL}/login", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=15_000)

    page.fill("#loginformemail",   TMS_USERNAME)
    page.fill("#loginformpassword", TMS_PASSWORD)
    page.click('button[type="submit"]')

    for i in range(20):
        page.wait_for_timeout(1000)
        if token:
            print(f"  [token] Ready after ~{i + 1}s")
            break

    if not token:
        raise RuntimeError("Login failed – token not captured. Check TMS_USERNAME/TMS_PASSWORD.")

    print(f"  Logged in. Current URL: {page.url}")
    return token


def _retrieve_for_type(page, rbe_type: str) -> list[dict]:
    """
    在告警页面选择 COMF 或 IOF，点击 Retrieve Active Alarms，
    捕获并返回 API 响应中的告警记录列表。
    同时打印页面上所有 API 调用，便于排查。
    """
    records: list[dict] = []
    api_log: list[str]  = []

    def on_resp(response):
        try:
            if TMS_API_BASE.replace("https://", "") not in response.url:
                return
            short = response.url.split("?")[0]
            data  = response.json() if response.status == 200 else None
            lst   = _extract_list(data) if data else None
            status_str = str(response.status)

            if lst:
                keys = list(lst[0].keys())
                api_log.append(f"{status_str} {short} → {len(lst)} rows, keys={keys}")
                if ALARM_RECORD_KEYS & set(keys):
                    print(f"    [capture] {short} → {len(lst)} alarm records, keys={keys}")
                    records.extend(lst)
            else:
                api_log.append(f"{status_str} {short}")
        except Exception:
            pass

    page.on("response", on_resp)

    # 每次都重新导航，确保页面状态干净
    alarm_url = f"{TMS_BASE_URL}{ALARM_PAGE}"
    print(f"  Navigating to: {alarm_url}")
    page.goto(alarm_url, timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=20_000)
    page.wait_for_timeout(2000)

    print(f"  Page title: {page.title()!r}  URL: {page.url}")

    # ── 选择告警类型 ──
    rbe_selected = False
    rbe_selectors = [
        f'input[value="{rbe_type}"]',
        f'input[value="{rbe_type.lower()}"]',
        f'button:has-text("{rbe_type}")',
        f'label:has-text("{rbe_type}")',
        f'mat-radio-button:has-text("{rbe_type}")',
        f'p-radiobutton:has-text("{rbe_type}")',
        f'li:has-text("{rbe_type}")',
        f':text-is("{rbe_type}")',
    ]
    for sel in rbe_selectors:
        try:
            page.click(sel, timeout=3000)
            print(f"  Selected {rbe_type} via: {sel!r}")
            rbe_selected = True
            break
        except Exception:
            pass
    if not rbe_selected:
        print(f"  WARNING: Could not click {rbe_type} selector – will try retrieve anyway")

    page.wait_for_timeout(500)

    # ── 点击 Retrieve Active Alarms ──
    retrieved = False
    retrieve_selectors = [
        'button:has-text("Retrieve Active Alarms")',
        'button:has-text("Retrieve")',
        'button:has-text("retrieve")',
        'a:has-text("Retrieve")',
        ':text("Retrieve Active Alarms")',
        'input[type="submit"]',
    ]
    for sel in retrieve_selectors:
        try:
            page.click(sel, timeout=4000)
            print(f"  Clicked retrieve via: {sel!r}")
            retrieved = True
            break
        except Exception:
            pass
    if not retrieved:
        print(f"  WARNING: Could not click Retrieve button")

    # 等待 API 响应
    page.wait_for_timeout(6000)

    # 移除监听，避免重复计数
    page.remove_listener("response", on_resp)

    # 打印本次观察到的所有 API 调用（排查用）
    print(f"\n  --- API calls for {rbe_type} ---")
    for line in api_log:
        print(f"    {line}")
    print(f"  --- end ({len(records)} alarm records captured) ---\n")

    return records


def collect_alarms() -> list[dict]:
    """主采集函数：登录 → 依次检索 COMF / IOF → 返回合并的原始记录。"""
    all_records: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page    = context.new_page()

        _do_login(page)

        for rbe_type in ("COMF", "IOF"):
            print(f"\n=== Retrieving {rbe_type} ===")
            recs = _retrieve_for_type(page, rbe_type)
            all_records.extend(recs)

        browser.close()

    print(f"\nTotal raw records captured: {len(all_records)}")
    return all_records


# ──────────────────────────────────────────────────────────
#  Data processing
# ──────────────────────────────────────────────────────────

def filter_ep1wm(raw: list[dict]) -> list[dict]:
    """只保留 Hardware Version = EP1WM 的记录。"""
    filtered = [
        r for r in raw
        if "EP1WM" in _get_field(r, *HW_VERSION_KEYS, default="").upper()
    ]
    print(f"EP1WM filter: {len(raw)} → {len(filtered)} records")
    if raw and not filtered:
        sample_hw = _get_field(raw[0], *HW_VERSION_KEYS, default="(not found)")
        print(f"  WARNING: No EP1WM records. Sample hardwareVersion field = {sample_hw!r}")
        print(f"  Sample record keys: {list(raw[0].keys())}")
    return filtered


def transform(raw_alarms: list[dict]) -> dict:
    records = []
    for alarm in raw_alarms:
        rbe_raw = _get_field(
            alarm,
            "rbe_type", "rbeType", "rbe", "alarmType", "alarm_type", "alarmCode",
            default=""
        ).upper()
        rbe = rbe_raw if rbe_raw in RBE_MAP else "COMF"

        tc_raw     = _get_field(alarm, "tc_code", "tcCode", "TC_Code", "tc", default="")
        tc_display = tc_raw if tc_raw else "-"

        status_date_raw = (
            alarm.get("status_date") or alarm.get("statusDate")
            or alarm.get("updated_at") or alarm.get("updatedAt")
            or alarm.get("created_at") or alarm.get("createdAt") or ""
        )
        try:
            dt = datetime.fromisoformat(str(status_date_raw).replace("Z", "+00:00"))
            status_date = dt.astimezone(SGT).strftime("%Y-%m-%d %H:%M")
        except Exception:
            status_date = str(status_date_raw)[:16] if status_date_raw else "-"

        records.append({
            "TC_Display":  tc_display,
            "Pfx":         _get_field(alarm, "prefix",  "Prefix",  "pfx"),
            "Block":       _get_field(alarm, "block",   "Block",   "blockNo",  "block_no"),
            "Lift":        _get_field(alarm, "lift",    "Lift",    "liftNo",   "lift_no", "liftId", "lift_id"),
            "Address":     _get_field(alarm, "address", "Address", "fullAddress", "full_address"),
            "LCOY":        _get_field(alarm, "lcoy",    "LCOY",    "Lcoy"),
            "Status Date": status_date,
            "RBE":         rbe,
            "RBE_Display": rbe,
            "Status":      _get_field(alarm, "status", "Status", "alarmStatus", "alarm_status", default="SET"),
        })

    comf = [r for r in records if r["RBE"] == "COMF"]
    iof  = [r for r in records if r["RBE"] == "IOF"]

    tc_stats: dict[str, dict[str, int]] = {"COMF": {}, "IOF": {}}
    for r in comf:
        tc_stats["COMF"][r["TC_Display"]] = tc_stats["COMF"].get(r["TC_Display"], 0) + 1
    for r in iof:
        tc_stats["IOF"][r["TC_Display"]]  = tc_stats["IOF"].get(r["TC_Display"],  0) + 1

    return {
        "records":      records,
        "comf_count":   len(comf),
        "iof_count":    len(iof),
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


# ──────────────────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────────────────

def main() -> None:
    if not TMS_BASE_URL:
        print("ERROR: TMS_BASE_URL is empty.")
        return
    if not ELTI_WORKER_URL:
        print("ERROR: ELTI_WORKER_URL is empty.")
        return

    print(f"TMS_BASE_URL:    {TMS_BASE_URL}")
    print(f"ELTI_WORKER_URL: {ELTI_WORKER_URL}")

    raw = collect_alarms()

    if raw:
        print(f"\nSample record keys:   {list(raw[0].keys())}")
        print(f"Sample record:        {raw[0]}")
        ep1wm = filter_ep1wm(raw)
    else:
        print("WARNING: No records captured at all.")
        ep1wm = []

    payload = transform(ep1wm)
    print(f"Transformed: comf_count={payload['comf_count']}, iof_count={payload['iof_count']}")
    push_to_worker(payload)


if __name__ == "__main__":
    main()

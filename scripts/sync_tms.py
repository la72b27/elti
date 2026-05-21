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

TMS_BASE_URL      = get_env_url("TMS_BASE_URL")
TMS_USERNAME      = os.environ.get("TMS_USERNAME", "")
TMS_PASSWORD      = os.environ.get("TMS_PASSWORD", "")
ELTI_WORKER_URL   = get_env_url("ELTI_WORKER_URL")
ELTI_UPDATE_TOKEN = os.environ.get("ELTI_UPDATE_TOKEN", "")

TMS_API_BASE = "https://tms-production-api.azure.surbana.tech"
ALARM_PAGE   = "/lift/tms-lmd-alarm"

SGT     = timezone(timedelta(hours=8))
RBE_MAP = {"COMF": "COMF", "IOF": "IOF"}

HW_VERSION_KEYS = (
    "hardwareVersion", "hardware_version", "hwVersion", "hw_version",
    "Hardware Version", "HardwareVersion",
)
ALARM_RECORD_KEYS = {
    "block", "Block", "blockNo",
    "lift",  "Lift",  "liftNo", "liftId",
    "address", "Address",
    "tc_code", "tcCode",
    "rbe_type", "rbeType",
    "hardwareVersion", "hardware_version", "hwVersion",
    "Hardware Version",
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
#  Login  (wait for Angular to complete its own redirect)
# ──────────────────────────────────────────────────────────

def _do_login(page) -> str:
    """
    登录 TMS。
    等待条件：token 已捕获 AND URL 已离开 /login（Angular 完成 redirect）。
    """
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
            # 保留最长的 token（auth token 比 validation token 长）
            if isinstance(t, str) and len(t) > 100 and len(t) > len(token):
                print(f"  [token] {response.url.split('?')[0]} ({len(t)} chars)")
                token = t
        except Exception:
            pass

    page.on("response", on_resp)

    print(f"  Logging in: {TMS_BASE_URL}/login")
    page.goto(f"{TMS_BASE_URL}/login", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=15_000)

    page.fill("#loginformemail",    TMS_USERNAME)
    page.fill("#loginformpassword", TMS_PASSWORD)
    page.click('button[type="submit"]')

    # 等待两个条件同时满足：token 已捕获 + Angular 完成 redirect（URL 离开 /login）
    for i in range(30):
        page.wait_for_timeout(1000)
        cur = page.url
        if token and "login" not in cur.lower():
            print(f"  Login complete after ~{i + 1}s — redirected to: {cur}")
            break
    else:
        if not token:
            raise RuntimeError("Login failed – token not captured. Check credentials.")
        print(f"  Token captured but URL still: {page.url}  (will proceed anyway)")

    # 额外等待，让 Angular 完成 localStorage 写入和初始 API 调用
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(2000)

    print(f"  Auth token: {len(token)} chars")
    return token


# ──────────────────────────────────────────────────────────
#  Navigate to alarm page (with retry if guard redirects)
# ──────────────────────────────────────────────────────────

def _navigate_to_alarm_page(page) -> bool:
    alarm_url = f"{TMS_BASE_URL}{ALARM_PAGE}"

    for attempt in range(1, 4):
        print(f"  Navigate attempt {attempt}: {alarm_url}")
        page.goto(alarm_url, timeout=30_000)
        page.wait_for_load_state("networkidle", timeout=20_000)
        page.wait_for_timeout(2000)

        cur = page.url
        print(f"  URL after navigation: {cur}")

        if ALARM_PAGE in cur:
            print(f"  Navigation succeeded.")
            return True

        print(f"  Guard redirected to {cur!r}, waiting 3s before retry…")
        page.wait_for_timeout(3000)

    print("  ERROR: Could not navigate to alarm page after 3 attempts.")
    return False


# ──────────────────────────────────────────────────────────
#  Element inspector (debug only)
# ──────────────────────────────────────────────────────────

def _dump_elements(page) -> None:
    info = page.evaluate("""() => {
        const sel = [
            'button','input','select','option','label','a',
            'mat-select','mat-option','mat-radio-button',
            'p-dropdown','p-radiobutton','.p-dropdown',
            '[role="listbox"]','[role="option"]',
            '[role="radio"]','[role="button"]','[role="combobox"]',
        ].join(',');
        return Array.from(document.querySelectorAll(sel))
            .filter(el => {
                const t = (el.textContent || '').trim();
                return t.length > 0 && t.length < 80;
            })
            .slice(0, 50)
            .map(el => ({
                tag:   el.tagName.toLowerCase(),
                text:  (el.textContent || '').trim().substring(0, 60),
                cls:   (el.className   || '').toString().substring(0, 50),
                value: el.getAttribute('value') || '',
                type:  el.getAttribute('type')  || '',
                role:  el.getAttribute('role')  || '',
                id:    el.id || '',
            }));
    }""")
    print("  --- Page elements ---")
    for el in info:
        print(f"    {el}")
    print("  --- end ---")


# ──────────────────────────────────────────────────────────
#  Dropdown selection helper
# ──────────────────────────────────────────────────────────

def _dump_select_options(page) -> None:
    """打印页面上所有 <select> 及其 <option>，帮助确认正确的 value/text。"""
    data = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('select')).map((sel, i) => ({
            index: i,
            id:    sel.id   || '',
            name:  sel.name || '',
            cls:   (sel.className || '').toString().substring(0, 40),
            options: Array.from(sel.options).map(o => ({
                value: o.value, text: o.text.trim(), selected: o.selected
            }))
        }));
    }""")
    print("  --- <select> elements ---")
    for s in data:
        print(f"    select[{s['index']}] id={s['id']!r} name={s['name']!r} cls={s['cls']!r}")
        for o in s["options"]:
            print(f"      option: value={o['value']!r}  text={o['text']!r}  selected={o['selected']}")
    print("  --- end selects ---")


def _dump_buttons(page) -> None:
    """打印页面上所有按钮文字。"""
    btns = page.evaluate("""() => {
        return Array.from(document.querySelectorAll(
            'button, input[type="submit"], input[type="button"], [role="button"]'
        ))
        .map(b => ({
            tag:      b.tagName.toLowerCase(),
            text:     (b.textContent || b.value || '').trim().substring(0, 60),
            disabled: b.disabled,
            cls:      (b.className || '').toString().substring(0, 50),
        }))
        .filter(b => b.text.length > 0);
    }""")
    print("  --- Buttons ---")
    for b in btns:
        print(f"    {b}")
    print("  --- end buttons ---")


def _select_dropdown_option(page, option_text: str) -> bool:
    """
    先枚举 select 选项，按 value 或 text 包含关系匹配，
    直接设置 select.value 并触发 change/input 事件（Angular 监听 change）。
    """
    # 枚举所有 select，找到 value 或 text 含目标文字的 option，直接赋值
    result = page.evaluate("""(search) => {
        const selects = document.querySelectorAll('select');
        const debugInfo = [];
        for (const sel of selects) {
            const opts = Array.from(sel.options).map(o => o.value + '|' + o.text.trim());
            debugInfo.push({id: sel.id, opts});
            for (const opt of sel.options) {
                const v = opt.value.toUpperCase();
                const t = opt.text.trim().toUpperCase();
                const s = search.toUpperCase();
                if (v === s || t === s || v.includes(s) || t.includes(s)) {
                    sel.value = opt.value;
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                    sel.dispatchEvent(new Event('input',  {bubbles: true}));
                    return 'SET value=' + opt.value + ' text=' + opt.text.trim();
                }
            }
        }
        return 'NO_MATCH: ' + JSON.stringify(debugInfo);
    }""", option_text)

    print(f"    [select] {result}")
    if result and not result.startswith("NO_MATCH"):
        return True

    # fallback: Angular Material / PrimeNG
    for trigger_sel in ("mat-select", "[role='combobox']", "p-dropdown", ".p-dropdown"):
        try:
            page.click(trigger_sel, timeout=2000)
            page.wait_for_timeout(500)
            for opt_sel in (
                f"mat-option:has-text('{option_text}')",
                f".p-dropdown-item:has-text('{option_text}')",
                f"[role='option']:has-text('{option_text}')",
            ):
                try:
                    page.click(opt_sel, timeout=2000)
                    print(f"    [dropdown] {trigger_sel} → {opt_sel}")
                    return True
                except Exception:
                    pass
        except Exception:
            pass

    return False


# ──────────────────────────────────────────────────────────
#  Retrieve one alarm type (COMF or IOF), stay on same page
# ──────────────────────────────────────────────────────────

def _retrieve_one(page, rbe_type: str) -> list[dict]:
    records: list[dict] = []
    api_log: list[str]  = []

    def on_resp(response):
        try:
            if TMS_API_BASE.replace("https://", "") not in response.url:
                return
            short = response.url.split("?")[0]
            if response.status != 200:
                api_log.append(f"{response.status} {short}")
                return
            data = response.json()
            lst  = _extract_list(data)
            if lst:
                keys = list(lst[0].keys())
                api_log.append(f"200 {short} → {len(lst)} rows  keys={keys}")
                if ALARM_RECORD_KEYS & set(keys):
                    print(f"    [capture] {short} → {len(lst)} records  keys={keys}")
                    records.extend(lst)
            else:
                api_log.append(f"200 {short}")
        except Exception:
            pass

    page.on("response", on_resp)

    # ── 选择告警类型 ──
    print(f"  Selecting alarm type: {rbe_type}")
    _dump_select_options(page)
    selected = _select_dropdown_option(page, rbe_type)
    if not selected:
        print(f"  WARNING: Could not select {rbe_type} from dropdown")
    page.wait_for_timeout(800)

    # ── 打印按钮列表（确认 Retrieve 按钮文字）──
    _dump_buttons(page)

    # ── 点击 Retrieve Active Alarms ──
    # 用 JS 枚举所有按钮并打印，同时尝试点击匹配的按钮
    retrieved = False
    result = page.evaluate("""() => {
        const all = Array.from(document.querySelectorAll(
            'button, input[type="submit"], [role="button"]'
        ));
        const allTexts = all.map(b => (b.textContent || b.value || '').trim());
        // 尝试点击任何含 "retrieve" 的按钮（不区分大小写，无可见性限制）
        for (const b of all) {
            const t = (b.textContent || b.value || '').trim().toLowerCase();
            if (t.includes('retrieve')) {
                b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                return 'clicked: ' + (b.textContent || b.value || '').trim();
            }
        }
        return 'NOT_FOUND. All button texts: ' + JSON.stringify(allTexts.filter(t => t).slice(0, 15));
    }""")
    print(f"  [retrieve] {result}")
    if result and not result.startswith("NOT_FOUND"):
        retrieved = True
    else:
        print(f"  WARNING: Retrieve button not found")

    # 等待 API 响应
    try:
        page.wait_for_load_state("networkidle", timeout=12_000)
    except Exception:
        pass
    page.wait_for_timeout(4000)

    page.remove_listener("response", on_resp)

    print(f"  --- API calls ({rbe_type}) ---")
    for line in api_log:
        print(f"    {line}")
    print(f"  --- captured {len(records)} records ---")
    return records


# ──────────────────────────────────────────────────────────
#  Main browser flow
# ──────────────────────────────────────────────────────────

def collect_alarms() -> list[dict]:
    all_records: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page    = context.new_page()

        _do_login(page)

        ok = _navigate_to_alarm_page(page)
        if not ok:
            browser.close()
            return []

        # 打印页面元素（select 选项 + 按钮），便于排查选择器
        _dump_elements(page)
        _dump_select_options(page)
        _dump_buttons(page)

        # 在同一个已加载的页面上依次检索 COMF 和 IOF
        for rbe_type in ("COMF", "IOF"):
            print(f"\n=== {rbe_type} ===")
            recs = _retrieve_one(page, rbe_type)
            all_records.extend(recs)

        browser.close()

    print(f"\nTotal raw records: {len(all_records)}")
    return all_records


# ──────────────────────────────────────────────────────────
#  Data processing
# ──────────────────────────────────────────────────────────

def filter_ep1wm(raw: list[dict]) -> list[dict]:
    out = [
        r for r in raw
        if "EP1WM" in _get_field(r, *HW_VERSION_KEYS, default="").upper()
    ]
    print(f"EP1WM filter: {len(raw)} → {len(out)} records")
    if raw and not out:
        hw_sample = _get_field(raw[0], *HW_VERSION_KEYS, default="(not found)")
        print(f"  Sample hwVersion field value: {hw_sample!r}")
        print(f"  Sample record keys: {list(raw[0].keys())}")
    return out


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
        print(f"\nSample keys:   {list(raw[0].keys())}")
        print(f"Sample record: {raw[0]}")
        ep1wm = filter_ep1wm(raw)
    else:
        print("WARNING: No records captured.")
        ep1wm = []

    payload = transform(ep1wm)
    print(f"Transformed: comf_count={payload['comf_count']}, iof_count={payload['iof_count']}")
    push_to_worker(payload)


if __name__ == "__main__":
    main()

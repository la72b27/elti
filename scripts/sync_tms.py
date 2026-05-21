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
    "hardwareVersion", "hardware_version", "hwVersion",
    "Hardware Version", "HardwareVersion",
)


def _get_field(d: dict, *keys: str, default: str = "") -> str:
    for k in keys:
        v = d.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return default


# ──────────────────────────────────────────────────────────
#  Login
# ──────────────────────────────────────────────────────────

def _do_login(page) -> str:
    """登录并等待 Angular 完成 redirect，返回 auth token。"""
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

    print(f"  Logging in: {TMS_BASE_URL}/login")
    page.goto(f"{TMS_BASE_URL}/login", timeout=30_000)
    page.wait_for_load_state("networkidle", timeout=15_000)
    page.fill("#loginformemail",    TMS_USERNAME)
    page.fill("#loginformpassword", TMS_PASSWORD)
    page.click('button[type="submit"]')

    for i in range(30):
        page.wait_for_timeout(1000)
        if token and "login" not in page.url.lower():
            print(f"  Login done ~{i+1}s → {page.url}")
            break
    else:
        if not token:
            raise RuntimeError("Login failed – no token captured.")
        print(f"  Token ok, URL={page.url}")

    page.wait_for_load_state("networkidle", timeout=15_000)
    page.wait_for_timeout(2000)
    print(f"  Token length: {len(token)}")
    return token


# ──────────────────────────────────────────────────────────
#  Get alarm type catalog via API  (code → description)
# ──────────────────────────────────────────────────────────

def _fetch_alarm_catalog(token: str) -> dict[str, str]:
    """
    返回 {description_upper: code} 映射，例如:
      "COMMUNICATION FAILURE" → "COMF"
      "IN OPERATION FAILURE"  → "IOF"
    """
    catalog: dict[str, str] = {}
    try:
        with httpx.Client(verify=False) as client:
            resp = client.get(
                f"{TMS_API_BASE}/portalapi/tmsalarm/getAllTmsAlarms",
                params={"assetType": "LMD"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            if resp.status_code == 200:
                for item in resp.json() if isinstance(resp.json(), list) else []:
                    code = str(item.get("code", "")).upper()
                    desc = str(item.get("description", "")).upper()
                    if code and desc:
                        catalog[desc] = code
                print(f"  Alarm catalog: {len(catalog)} entries")
                for d, c in list(catalog.items())[:6]:
                    print(f"    {d!r} → {c!r}")
    except Exception as e:
        print(f"  WARNING: Could not fetch alarm catalog: {e}")
    return catalog


# ──────────────────────────────────────────────────────────
#  Navigate to alarm page
# ──────────────────────────────────────────────────────────

def _navigate_to_alarm_page(page) -> bool:
    url = f"{TMS_BASE_URL}{ALARM_PAGE}"
    for attempt in range(1, 4):
        print(f"  Navigate [{attempt}]: {url}")
        page.goto(url, timeout=30_000)
        page.wait_for_load_state("networkidle", timeout=20_000)
        page.wait_for_timeout(3000)
        cur = page.url
        print(f"  → {cur}")
        if ALARM_PAGE in cur:
            return True
        print(f"  Guard redirected, retrying in 3s…")
        page.wait_for_timeout(3000)
    print("  ERROR: could not land on alarm page")
    return False


# ──────────────────────────────────────────────────────────
#  DOM diagnostics
# ──────────────────────────────────────────────────────────

def _find_keyword_elements(page, *keywords: str) -> None:
    """找出页面上所有包含关键字的叶子节点元素，打印其 tag、text、class、parent。"""
    pattern = "|".join(keywords)
    results = page.evaluate(f"""() => {{
        const re = new RegExp('({pattern})', 'i');
        return Array.from(document.querySelectorAll('*'))
            .filter(el => el.childElementCount === 0 && re.test(el.textContent))
            .slice(0, 30)
            .map(el => ({{
                tag:  el.tagName.toLowerCase(),
                text: el.textContent.trim().substring(0, 80),
                cls:  (el.className || '').toString().substring(0, 50),
                pid:  el.parentElement?.id || '',
                ptag: el.parentElement?.tagName.toLowerCase() || '',
                pcls: (el.parentElement?.className || '').toString().substring(0, 50),
            }}));
    }}""")
    print(f"  --- Elements matching {keywords} ---")
    for r in results:
        print(f"    {r}")
    print("  --- end ---")


def _extract_all_tables(page) -> list[dict]:
    """
    提取页面上所有 <table> 的表头和数据行。
    返回列表，每项: {index, headers, rows (list of dicts), rowCount}
    """
    raw = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('table')).map((tbl, i) => {
            const ths = Array.from(tbl.querySelectorAll('thead th, thead td'))
                           .map(h => h.textContent.trim());
            const rows = Array.from(tbl.querySelectorAll('tbody tr')).map(tr =>
                Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim())
            ).filter(r => r.some(c => c));
            return {index: i, headers: ths, rows: rows};
        });
    }""")
    tables = []
    for t in raw:
        headers = t["headers"]
        dicts = []
        for row in t["rows"]:
            obj = {}
            for j, h in enumerate(headers):
                obj[h] = row[j] if j < len(row) else ""
            dicts.append(obj)
        tables.append({
            "index":    t["index"],
            "headers":  headers,
            "rows":     dicts,
            "rowCount": len(dicts),
        })
    return tables


# ──────────────────────────────────────────────────────────
#  Pagination helpers
# ──────────────────────────────────────────────────────────

def _pagination_state(page) -> dict:
    """
    返回当前分页状态：
      {current, total, has_next, has_prev, page_info_text}
    通过检查 <li class="page-item disabled"> 包裹 Next/Previous 的 <a> 判断。
    """
    return page.evaluate("""() => {
        // Bootstrap pagination: <li class="page-item [disabled]"><a class="page-link">Next</a></li>
        let hasNext = false, hasPrev = false, pageText = '';
        document.querySelectorAll('li.page-item, li').forEach(li => {
            const a = li.querySelector('a.page-link');
            if (!a) return;
            const t = a.textContent.trim();
            const disabled = li.classList.contains('disabled');
            if (t === 'Next' || t === '>|')    hasNext = !disabled;
            if (t === 'Previous' || t === '|<') hasPrev = !disabled;
        });
        // Also try plain <a class="page-link"> without <li> wrapper
        if (!hasNext) {
            document.querySelectorAll('a.page-link').forEach(a => {
                const t = a.textContent.trim();
                if ((t === 'Next' || t === '>|') && !a.closest('li.disabled')) hasNext = true;
            });
        }
        // Try to find current page indicator text (e.g. "Page 1 of 5" or "1-20 / 100")
        const pageInfoEl = document.querySelector(
            '.pagination-info, .page-info, [class*="page-info"], [class*="pageInfo"]'
        );
        if (pageInfoEl) pageText = pageInfoEl.textContent.trim();
        return {hasNext, hasPrev, pageText};
    }""")


def _click_next_page(page) -> bool:
    """
    点击 Next 或 >| 分页按钮，等待新数据渲染，返回是否成功。
    """
    clicked = page.evaluate("""() => {
        // Try Bootstrap li > a pattern first
        for (const li of document.querySelectorAll('li.page-item')) {
            if (li.classList.contains('disabled')) continue;
            const a = li.querySelector('a.page-link');
            if (a && (a.textContent.trim() === 'Next' || a.textContent.trim() === '>|')) {
                a.click();
                return true;
            }
        }
        // Fallback: plain <a class="page-link">
        for (const a of document.querySelectorAll('a.page-link')) {
            const t = a.textContent.trim();
            if ((t === 'Next' || t === '>|') && !a.closest('li.disabled')) {
                a.click();
                return true;
            }
        }
        return false;
    }""")
    if clicked:
        page.wait_for_timeout(1500)
        try:
            page.wait_for_load_state("networkidle", timeout=8_000)
        except Exception:
            pass
        page.wait_for_timeout(500)
    return bool(clicked)


def _extract_alarm_rows_all_pages(page, rbe_hint: str, max_pages: int = 200) -> list[dict]:
    """
    从当前 tab/section 提取所有分页数据。
    自动翻页直到 Next 按钮被禁用或超过 max_pages。
    """
    ALARM_HEADERS = {"TC", "Block", "Address", "Status Date", "Bits Description"}
    all_rows: list[dict] = []
    page_num = 1

    while True:
        tables = _extract_all_tables(page)
        page_rows: list[dict] = []
        for tbl in tables:
            if ALARM_HEADERS & set(tbl["headers"]):
                page_rows.extend(tbl["rows"])

        if page_rows:
            for row in page_rows:
                row["_rbe_hint"] = rbe_hint
            all_rows.extend(page_rows)

        state = _pagination_state(page)
        print(f"    Page {page_num}: {len(page_rows)} rows | "
              f"next={state['hasNext']} {state['pageText']}")

        if not state["hasNext"] or not page_rows:
            break
        if page_num >= max_pages:
            print(f"    WARNING: reached max_pages={max_pages}, stopping")
            break

        if not _click_next_page(page):
            print("    Could not click Next, stopping pagination")
            break

        page_num += 1

    print(f"  Total rows across {page_num} page(s): {len(all_rows)}")
    return all_rows


# ──────────────────────────────────────────────────────────
#  Click COMF / IOF tab (if tabs exist)
# ──────────────────────────────────────────────────────────

def _click_tab(page, rbe_type: str) -> bool:
    """
    尝试点击文本为 rbe_type (COMF/IOF) 的 Tab 元素，
    支持 <a>、<li>、<button>、<div>、<span> 等。
    """
    result = page.evaluate("""(text) => {
        const all = Array.from(document.querySelectorAll(
            'a,li,button,div,span,[role="tab"]'
        ));
        for (const el of all) {
            const t = el.textContent.trim();
            if (t === text || t.startsWith(text + ' ') || t.endsWith(' ' + text)) {
                el.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                return el.tagName + ': ' + t.substring(0, 40);
            }
        }
        return null;
    }""", rbe_type)
    if result:
        print(f"  [tab] Clicked {rbe_type}: {result}")
        return True
    print(f"  [tab] No tab found for {rbe_type}")
    return False


# ──────────────────────────────────────────────────────────
#  Main browser flow
# ──────────────────────────────────────────────────────────

def collect_alarms() -> tuple[list[dict], dict[str, str]]:
    """
    返回 (raw_records, alarm_catalog)。
    raw_records 是从 DOM 表格提取的原始行数据（含所有列）。
    alarm_catalog 用于将 Bits Description 映射回 COMF/IOF。
    """
    all_rows: list[dict] = []
    alarm_catalog: dict[str, str] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page    = context.new_page()

        token = _do_login(page)
        alarm_catalog = _fetch_alarm_catalog(token)

        ok = _navigate_to_alarm_page(page)
        if not ok:
            browser.close()
            return [], alarm_catalog

        # ── 诊断：找 COMF/IOF/Retrieve 关键字元素 ──
        _find_keyword_elements(page, "COMF", "IOF", "Retrieve", "Active Alarm")

        # ── 依次点击 COMF 和 IOF tab，逐页提取所有数据 ──
        for rbe_type in ("COMF", "IOF"):
            print(f"\n=== {rbe_type} ===")
            clicked = _click_tab(page, rbe_type)
            if clicked:
                page.wait_for_timeout(3000)
                try:
                    page.wait_for_load_state("networkidle", timeout=8_000)
                except Exception:
                    pass

            # 先打印一次表格结构，便于诊断
            tables = _extract_all_tables(page)
            print(f"  Tables found: {len(tables)}")
            for tbl in tables:
                print(f"  Table[{tbl['index']}]: {tbl['rowCount']} rows, "
                      f"headers={tbl['headers']}")
                if tbl["rows"]:
                    print(f"    Sample row: {tbl['rows'][0]}")

            # 带分页的完整提取
            rows = _extract_alarm_rows_all_pages(page, rbe_hint=rbe_type)
            all_rows.extend(rows)

        browser.close()

    print(f"\nTotal rows extracted from DOM: {len(all_rows)}")
    return all_rows, alarm_catalog


# ──────────────────────────────────────────────────────────
#  Data processing
# ──────────────────────────────────────────────────────────

def filter_ep1wm(rows: list[dict]) -> list[dict]:
    out = [r for r in rows if "EP1WM" in r.get("Hardware Version", "").upper()]
    print(f"EP1WM filter: {len(rows)} → {len(out)} records")
    if rows and not out:
        sample_hw = rows[0].get("Hardware Version", "(not found)")
        print(f"  Sample 'Hardware Version': {sample_hw!r}")
        print(f"  All column names: {list(rows[0].keys())}")
    return out


def transform(rows: list[dict], alarm_catalog: dict[str, str]) -> dict:
    """
    将 DOM 表格行转换为 ELTI 数据格式。
    用 alarm_catalog (description→code) 将 Bits Description 映射到 COMF/IOF。
    """
    records = []
    for row in rows:
        # 确定 RBE 类型
        bits_desc = row.get("Bits Description", "").upper()
        rbe = alarm_catalog.get(bits_desc, "")
        if not rbe:
            # 尝试 description 前缀匹配
            for desc, code in alarm_catalog.items():
                if bits_desc.startswith(desc[:8]) or desc.startswith(bits_desc[:8]):
                    rbe = code
                    break
        if not rbe:
            rbe = row.get("_rbe_hint", "COMF")
        rbe = rbe if rbe in RBE_MAP else "COMF"

        # 解析时间
        status_date_raw = row.get("Status Date", "")
        try:
            dt = datetime.fromisoformat(status_date_raw.replace("Z", "+00:00"))
            status_date = dt.astimezone(SGT).strftime("%Y-%m-%d %H:%M")
        except Exception:
            status_date = status_date_raw[:16] if status_date_raw else "-"

        records.append({
            "TC_Display":  row.get("TC", "-"),
            "Pfx":         row.get("Pfx", ""),
            "Block":       row.get("Block", ""),
            "Lift":        row.get("Lift", row.get("Lift Company", "")),
            "Address":     row.get("Address", ""),
            "LCOY":        row.get("LCOY", ""),
            "Status Date": status_date,
            "RBE":         rbe,
            "RBE_Display": rbe,
            "Status":      row.get("Status", "SET"),
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

    raw_rows, alarm_catalog = collect_alarms()

    if not raw_rows:
        print("WARNING: No rows extracted from DOM.")
        push_to_worker(transform([], alarm_catalog))
        return

    ep1wm = filter_ep1wm(raw_rows)
    payload = transform(ep1wm, alarm_catalog)
    print(f"Transformed: comf_count={payload['comf_count']}, iof_count={payload['iof_count']}")
    push_to_worker(payload)


if __name__ == "__main__":
    main()

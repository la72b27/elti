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

# 结果表的特征列（告警记录），区别于参考表（Bits/Abbr/Field Description）
RESULT_HEADERS  = {"TC", "Block", "Address", "Status Date"}
RESULT_HEADERS2 = {"TC", "Pfx", "Block", "Hardware Version"}  # 备选组合

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
    return token


# ──────────────────────────────────────────────────────────
#  Alarm catalog via API
# ──────────────────────────────────────────────────────────

def _fetch_alarm_catalog(token: str) -> dict[str, str]:
    """返回 {description_upper: code} e.g. "COMMUNICATION FAILURE" → "COMF" """
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
                for item in (resp.json() if isinstance(resp.json(), list) else []):
                    code = str(item.get("code", "")).upper()
                    desc = str(item.get("description", "")).upper()
                    if code and desc:
                        catalog[desc] = code
                print(f"  Alarm catalog: {len(catalog)} entries")
    except Exception as e:
        print(f"  WARNING: catalog fetch failed: {e}")
    return catalog


# ──────────────────────────────────────────────────────────
#  Navigate
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
        page.wait_for_timeout(3000)
    print("  ERROR: Could not land on alarm page")
    return False


# ──────────────────────────────────────────────────────────
#  Table helpers
# ──────────────────────────────────────────────────────────

def _extract_all_tables(page) -> list[dict]:
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
        dicts = []
        for row in t["rows"]:
            obj = {t["headers"][j]: row[j] for j in range(min(len(t["headers"]), len(row)))}
            dicts.append(obj)
        tables.append({"index": t["index"], "headers": t["headers"],
                        "rows": dicts, "rowCount": len(dicts)})
    return tables


def _is_result_table(headers: list[str]) -> bool:
    """判断是否为告警结果表（不是参考表）。"""
    hdrs = set(headers)
    return bool((RESULT_HEADERS & hdrs) or (RESULT_HEADERS2 & hdrs))


# ──────────────────────────────────────────────────────────
#  Select alarm type by clicking the row in the reference table
# ──────────────────────────────────────────────────────────

def _click_alarm_type_row(page, abbr: str) -> bool:
    """
    在参考表（Bits/Abbr/Field Description）中找到 Abbr=abbr 的行并点击。
    同时尝试点击 <tr> 父元素（触发行选择事件）。
    """
    result = page.evaluate("""(abbr) => {
        // 找所有 class="fit" 的 td（Abbr 列），内容匹配
        const tds = Array.from(document.querySelectorAll('td.fit'));
        for (const td of tds) {
            if (td.textContent.trim() === abbr) {
                // 点击 td 本身
                td.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                // 同时点击父 tr
                if (td.parentElement && td.parentElement.tagName === 'TR') {
                    td.parentElement.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                }
                const desc = td.parentElement
                    ? Array.from(td.parentElement.querySelectorAll('td'))
                        .map(t => t.textContent.trim()).join(' | ')
                    : abbr;
                return 'Row clicked: ' + desc.substring(0, 60);
            }
        }
        return null;
    }""", abbr)

    if result:
        print(f"  [row-select] {result}")
        return True
    print(f"  [row-select] Row with Abbr={abbr!r} not found")
    return False


# ──────────────────────────────────────────────────────────
#  Find and click Retrieve Active Alarms button
# ──────────────────────────────────────────────────────────

def _click_retrieve_button(page) -> bool:
    """
    找到 Retrieve Active Alarms 按钮并点击。
    包含 hidden/disabled 状态的按钮也尝试。
    """
    result = page.evaluate("""() => {
        const keywords = [
            'retrieve active alarms', 'retrieve active alarm',
            'retrieve', 'search', 'get alarms', 'get active',
        ];
        const all = Array.from(document.querySelectorAll(
            'button, input[type="submit"], input[type="button"], [role="button"], a.btn'
        ));
        // 打印所有按钮文字用于诊断
        const allTexts = all.map(b => (b.textContent || b.value || '').trim())
                            .filter(t => t.length > 0 && t.length < 80);
        console.log('All buttons:', JSON.stringify(allTexts));

        for (const kw of keywords) {
            for (const b of all) {
                const t = (b.textContent || b.value || '').trim().toLowerCase();
                if (t.includes(kw)) {
                    b.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                    return 'Clicked: ' + (b.textContent || b.value || '').trim();
                }
            }
        }
        return 'NOT_FOUND: ' + JSON.stringify(allTexts.slice(0, 20));
    }""")
    print(f"  [retrieve-btn] {result}")
    return bool(result) and not result.startswith("NOT_FOUND")


# ──────────────────────────────────────────────────────────
#  Pagination for RESULTS table only
# ──────────────────────────────────────────────────────────

def _result_table_next_page(page, prev_first_row: str) -> bool:
    """
    点击 Next 分页按钮，并验证内容确实变化（防止死循环）。
    返回 True 表示成功翻页，False 表示已是最后一页或内容未变化。
    """
    # 检查 Next 按钮状态
    has_next = page.evaluate("""() => {
        for (const li of document.querySelectorAll('li.page-item')) {
            if (li.classList.contains('disabled')) continue;
            const a = li.querySelector('a.page-link');
            if (a && (a.textContent.trim() === 'Next' || a.textContent.trim() === '>|'))
                return true;
        }
        // fallback: plain <a> not inside disabled li
        for (const a of document.querySelectorAll('a.page-link')) {
            const t = a.textContent.trim();
            if ((t === 'Next' || t === '>|') && !a.closest('li.disabled'))
                return true;
        }
        return false;
    }""")
    if not has_next:
        return False

    # 点击 Next
    page.evaluate("""() => {
        for (const li of document.querySelectorAll('li.page-item')) {
            if (li.classList.contains('disabled')) continue;
            const a = li.querySelector('a.page-link');
            if (a && (a.textContent.trim() === 'Next' || a.textContent.trim() === '>|')) {
                a.click(); return;
            }
        }
        for (const a of document.querySelectorAll('a.page-link')) {
            const t = a.textContent.trim();
            if ((t === 'Next' || t === '>|') && !a.closest('li.disabled')) {
                a.click(); return;
            }
        }
    }""")
    page.wait_for_timeout(1500)
    try:
        page.wait_for_load_state("networkidle", timeout=6_000)
    except Exception:
        pass
    page.wait_for_timeout(500)

    # 检查内容是否变化（防死循环）
    tables = _extract_all_tables(page)
    for tbl in tables:
        if _is_result_table(tbl["headers"]) and tbl["rows"]:
            new_first = str(tbl["rows"][0])
            if new_first == prev_first_row:
                print("    Content unchanged after Next click — stopping pagination")
                return False
            return True
    return False


def _extract_results_all_pages(page, rbe_hint: str, max_pages: int = 500) -> list[dict]:
    """
    从结果表（TC/Pfx/Block/Address 等列）提取所有分页数据。
    参考表（Bits/Abbr/Field Description）完全忽略。
    """
    all_rows: list[dict] = []
    page_num  = 1
    prev_first = ""

    while True:
        tables = _extract_all_tables(page)

        # 只取结果表，忽略参考表
        page_rows: list[dict] = []
        for tbl in tables:
            if _is_result_table(tbl["headers"]):
                page_rows.extend(tbl["rows"])

        if page_rows:
            for row in page_rows:
                row["_rbe_hint"] = rbe_hint
            all_rows.extend(page_rows)
            prev_first = str(page_rows[0])
        else:
            print(f"    Page {page_num}: result table not found / empty")
            if page_num == 1:
                # 第一页就没有数据，列出所有表的表头帮助诊断
                for tbl in tables:
                    print(f"      Table[{tbl['index']}] headers={tbl['headers']} "
                          f"rows={tbl['rowCount']}")
            break

        print(f"    Page {page_num}: {len(page_rows)} rows (total so far: {len(all_rows)})")

        if page_num >= max_pages:
            print(f"    Reached max_pages={max_pages}, stopping")
            break

        if not _result_table_next_page(page, prev_first):
            break

        page_num += 1

    print(f"  Extracted {len(all_rows)} rows across {page_num} page(s)")
    return all_rows


# ──────────────────────────────────────────────────────────
#  Main browser flow
# ──────────────────────────────────────────────────────────

def collect_alarms() -> tuple[list[dict], dict[str, str]]:
    all_rows: list[dict] = []
    alarm_catalog: dict[str, str] = {}
    api_calls: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page    = context.new_page()

        # 全程捕获 TMS API 响应，用于诊断
        def on_resp(response):
            try:
                if TMS_API_BASE.replace("https://", "") not in response.url:
                    return
                short = response.url.split("?")[0]
                data  = None
                if response.status == 200:
                    try:
                        data = response.json()
                    except Exception:
                        pass
                if data:
                    if isinstance(data, list):
                        keys = list(data[0].keys()) if data else []
                        api_calls.append(f"{response.status} {short} → {len(data)} items, keys={keys}")
                    elif isinstance(data, dict):
                        api_calls.append(f"{response.status} {short} → dict keys={list(data.keys())[:5]}")
                else:
                    api_calls.append(f"{response.status} {short}")
            except Exception:
                pass

        page.on("response", on_resp)

        token = _do_login(page)
        alarm_catalog = _fetch_alarm_catalog(token)

        ok = _navigate_to_alarm_page(page)
        if not ok:
            browser.close()
            return [], alarm_catalog

        # 对每种告警类型：选行 → 点 Retrieve → 提取结果表所有分页
        for rbe_type in ("COMF", "IOF"):
            print(f"\n=== {rbe_type} ===")
            api_calls.clear()

            row_clicked = _click_alarm_type_row(page, rbe_type)
            page.wait_for_timeout(1000)

            # 点击后等待 DOM 更新
            try:
                page.wait_for_load_state("networkidle", timeout=5_000)
            except Exception:
                pass
            page.wait_for_timeout(1000)

            retrieve_clicked = _click_retrieve_button(page)
            if retrieve_clicked:
                page.wait_for_timeout(2000)
                try:
                    page.wait_for_load_state("networkidle", timeout=10_000)
                except Exception:
                    pass
                page.wait_for_timeout(1000)

            # 打印此轮 API 调用（帮助确认正确端点）
            print(f"  --- API calls after {rbe_type} ---")
            for line in api_calls:
                print(f"    {line}")
            print("  --- end ---")

            rows = _extract_results_all_pages(page, rbe_hint=rbe_type)
            all_rows.extend(rows)

        browser.close()

    print(f"\nTotal rows: {len(all_rows)}")
    return all_rows, alarm_catalog


# ──────────────────────────────────────────────────────────
#  Data processing
# ──────────────────────────────────────────────────────────

def filter_ep1wm(rows: list[dict]) -> list[dict]:
    out = [r for r in rows if "EP1WM" in r.get("Hardware Version", "").upper()]
    print(f"EP1WM filter: {len(rows)} → {len(out)} records")
    if rows and not out:
        print(f"  Sample 'Hardware Version': {rows[0].get('Hardware Version', '(not found)')!r}")
        print(f"  Column names: {list(rows[0].keys())}")
    return out


def transform(rows: list[dict], alarm_catalog: dict[str, str]) -> dict:
    records = []
    for row in rows:
        bits_desc = row.get("Bits Description", "").upper()
        rbe = alarm_catalog.get(bits_desc, "")
        if not rbe:
            for desc, code in alarm_catalog.items():
                if bits_desc and (bits_desc[:8] == desc[:8]):
                    rbe = code
                    break
        if not rbe:
            rbe = row.get("_rbe_hint", "COMF")
        rbe = rbe if rbe in RBE_MAP else "COMF"

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
        print("WARNING: No rows extracted.")
        push_to_worker(transform([], alarm_catalog))
        return

    print(f"Sample columns: {list(raw_rows[0].keys())}")
    print(f"Sample row:     {raw_rows[0]}")

    ep1wm   = filter_ep1wm(raw_rows)
    payload = transform(ep1wm, alarm_catalog)
    print(f"Transformed: comf_count={payload['comf_count']}, iof_count={payload['iof_count']}")
    push_to_worker(payload)


if __name__ == "__main__":
    main()

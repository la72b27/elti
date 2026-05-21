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

SGT     = timezone(timedelta(hours=8))
RBE_MAP = {"COMF": "COMF", "IOF": "IOF"}

# Bits Description → RBE Display（与 elti_web.py 保持一致）
BITS_TO_RBE = {
    "Communication Failure":        "COMF",
    "I/O Serial Comm Cable Faulty": "IOF",
}


# ──────────────────────────────────────────────────────────
#  Login
# ──────────────────────────────────────────────────────────

def _do_login(page) -> None:
    """登录 TMS，等待 Angular 完成 redirect 后返回。"""
    print(f"Logging in: {TMS_BASE_URL}/login")
    page.goto(f"{TMS_BASE_URL}/login", wait_until="networkidle")
    page.fill("#loginformemail",    TMS_USERNAME)
    page.fill("#loginformpassword", TMS_PASSWORD)
    page.click("button:has-text('Login'), button[type='submit']")
    page.wait_for_timeout(5000)
    print(f"Login done. URL: {page.url}")


# ──────────────────────────────────────────────────────────
#  Fetch one alarm type (COMF or IOF) with auto-pagination
#  直接移植自 elti_web.py  get_all_pages_data()
# ──────────────────────────────────────────────────────────

def get_all_pages_data(page, alarm_code: str) -> list[dict]:
    """
    1. 在 searchable dropdown 搜索并选择 alarm_code
    2. 点击 Retrieve Active Alarms
    3. 逐页抓取 app-tms-alarm-base tbody tr
    4. 只保留 Hardware Version == EP1WM 的行
    5. 返回列表，每项包含 10 个字段
    """
    print(f"Fetching {alarm_code} data...")

    # ── 1. 选择告警类型 ──
    try:
        alarm_dropdown = page.wait_for_selector(
            "#tmsAlarm2, #tmsAlarm1, .alarm-select app-searchable-dropdown",
            timeout=10_000,
        )
        alarm_dropdown.click()
        search_input = alarm_dropdown.query_selector("input[placeholder='Search']")
        search_input.fill(alarm_code)
        page.wait_for_timeout(1000)
        option = page.wait_for_selector(f"td:has-text('{alarm_code}')", timeout=5000)
        option.click()
        print(f"  Selected {alarm_code} from dropdown")
    except Exception as e:
        print(f"  ERROR selecting alarm {alarm_code}: {e}")
        return []

    # ── 2. 点击 Retrieve Active Alarms ──
    try:
        retrieve_btn = page.wait_for_selector(
            "button:has-text('Retrieve Active Alarms')", timeout=10_000
        )
        retrieve_btn.click()
        page.wait_for_timeout(5000)
        print(f"  Clicked 'Retrieve Active Alarms'")
    except Exception as e:
        print(f"  ERROR clicking Retrieve: {e}")
        return []

    # ── 3. 逐页抓取 ──
    all_data: list[dict] = []
    page_num = 1

    while True:
        print(f"  Scraping page {page_num}...")
        page.wait_for_timeout(2000)

        rows = page.query_selector_all("app-tms-alarm-base tbody tr")
        page_ep1wm = 0
        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) < 10:
                continue
            text_cells = [c.inner_text().strip() for c in cells]
            if "No records available" in text_cells[0]:
                continue

            row_data = {
                "TC_Display":       text_cells[0],
                "Pfx":              text_cells[1],
                "Block":            text_cells[2],
                "Lift":             text_cells[3],
                "Address":          text_cells[4],
                "Hardware Version": text_cells[5],
                "LCOY":             text_cells[6],
                "Status Date":      text_cells[7],
                "Bits Description": text_cells[8],
                "Status":           text_cells[9],
                "RBE":              alarm_code,
            }

            # 只保留 EP1WM
            if row_data["Hardware Version"] == "EP1WM":
                row_data["RBE_Display"] = BITS_TO_RBE.get(
                    row_data["Bits Description"], alarm_code
                )
                all_data.append(row_data)
                page_ep1wm += 1

        print(f"    rows={len(rows)}  EP1WM={page_ep1wm}  total={len(all_data)}")

        # ── 4. 翻页 ──
        next_btn = page.query_selector(
            "li.page-item:not(.disabled) a:has-text('Next')"
        )
        if next_btn:
            next_btn.click()
            page.wait_for_timeout(3000)
            page_num += 1
        else:
            print(f"  No more pages (total pages: {page_num})")
            break

    return all_data


# ──────────────────────────────────────────────────────────
#  Merge records：按 TC_Display+Pfx+Block 合并，Lift 拼接
#  直接移植自 elti_web.py  merge_records()
# ──────────────────────────────────────────────────────────

def merge_records(records: list[dict]) -> list[dict]:
    if not records:
        return []
    from itertools import groupby
    key_fn = lambda r: (r.get("TC_Display",""), r.get("Pfx",""), r.get("Block",""))
    sorted_recs = sorted(records, key=key_fn)
    merged = []
    for key, group_iter in groupby(sorted_recs, key=key_fn):
        group = list(group_iter)
        base = {k: v for k, v in group[0].items()}
        lifts = sorted({str(r.get("Lift","")) for r in group if r.get("Lift","")})
        base["Lift"] = "".join(lifts)
        merged.append(base)
    return merged


# ──────────────────────────────────────────────────────────
#  Transform to ELTI payload
# ──────────────────────────────────────────────────────────

def build_payload(comf_records: list[dict], iof_records: list[dict]) -> dict:
    records = []
    for r in comf_records + iof_records:
        status_date_raw = r.get("Status Date", "")
        # 匹配任意格式末尾的 H:MM 或 HH:MM，零补位后原样保留日期部分
        import re as _re
        _m = _re.match(r'^(.*?)\s+(\d{1,2}):(\d{1,2})$', (status_date_raw or "").strip())
        if _m:
            status_date = (f"{_m.group(1)} "
                           f"{_m.group(2).zfill(2)}:{_m.group(3).zfill(2)}")
        else:
            try:
                dt = datetime.fromisoformat(status_date_raw.replace("Z", "+00:00"))
                status_date = dt.astimezone(SGT).strftime("%Y-%m-%d %H:%M")
            except Exception:
                status_date = status_date_raw if status_date_raw else "-"

        records.append({
            "TC_Display":  r.get("TC_Display", "-"),
            "Pfx":         r.get("Pfx", ""),
            "Block":       r.get("Block", ""),
            "Lift":        r.get("Lift", ""),
            "Address":     r.get("Address", ""),
            "LCOY":        r.get("LCOY", ""),
            "Status Date": status_date,
            "RBE":         r.get("RBE_Display", r.get("RBE", "COMF")),
            "RBE_Display": r.get("RBE_Display", r.get("RBE", "COMF")),
            "Status":      r.get("Status", "SET"),
        })

    comf_out = [r for r in records if r["RBE"] == "COMF"]
    iof_out  = [r for r in records if r["RBE"] == "IOF"]

    tc_stats: dict[str, dict[str, int]] = {"COMF": {}, "IOF": {}}
    for r in comf_out:
        tc = r["TC_Display"]
        tc_stats["COMF"][tc] = tc_stats["COMF"].get(tc, 0) + 1
    for r in iof_out:
        tc = r["TC_Display"]
        tc_stats["IOF"][tc] = tc_stats["IOF"].get(tc, 0) + 1

    return {
        "records":      records,
        "comf_count":   len(comf_out),
        "iof_count":    len(iof_out),
        "tc_stats":     tc_stats,
        "last_updated": datetime.now(SGT).strftime("%Y-%m-%d %H:%M"),
    }


# ──────────────────────────────────────────────────────────
#  Push to Cloudflare Worker
# ──────────────────────────────────────────────────────────

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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page    = context.new_page()

        _do_login(page)

        print("\nNavigating to alarm page...")
        page.goto(
            f"{TMS_BASE_URL}/lift/tms-lmd-alarm",
            wait_until="networkidle",
        )
        page.wait_for_timeout(5000)
        print(f"Alarm page URL: {page.url}")

        comf_raw     = get_all_pages_data(page, "COMF")
        comf_records = merge_records(comf_raw)
        print(f"COMF: {len(comf_raw)} raw → {len(comf_records)} merged")

        iof_raw      = get_all_pages_data(page, "IOF")
        iof_records  = merge_records(iof_raw)
        print(f"IOF:  {len(iof_raw)} raw → {len(iof_records)} merged")

        browser.close()

    payload = build_payload(comf_records, iof_records)
    print(f"Payload: comf={payload['comf_count']}  iof={payload['iof_count']}")
    push_to_worker(payload)


if __name__ == "__main__":
    main()

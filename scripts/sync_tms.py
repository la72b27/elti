import os
import json
import httpx
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

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

TMS_API_HOST = "tms-production-api.azure.surbana.tech"

SGT = timezone(timedelta(hours=8))

RBE_MAP = {"COMF": "COMF", "IOF": "IOF"}


def fetch_alarms_via_browser() -> list[dict]:
    captured = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        def handle_response(response):
            try:
                url = response.url
                if TMS_API_HOST in url and "tmsalarm" in url and response.status == 200:
                    data = response.json()
                    print(f"DEBUG intercepted: {url} → {type(data)}")
                    if isinstance(data, list):
                        captured["alarms"] = data
                    elif isinstance(data, dict) and "data" in data:
                        captured["alarms"] = data["data"]
            except Exception as e:
                print(f"DEBUG response parse error: {e}")

        page.on("response", handle_response)

        print(f"DEBUG: Navigating to {TMS_BASE_URL}/login")
        page.goto(f"{TMS_BASE_URL}/login", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        print(f"DEBUG: Login page URL: {page.url}")
        print(f"DEBUG: Page title: {page.title()}")

        inputs = page.query_selector_all("input")
        for i, inp in enumerate(inputs):
            print(f"DEBUG input[{i}]: type={inp.get_attribute('type')} name={inp.get_attribute('name')} id={inp.get_attribute('id')} placeholder={inp.get_attribute('placeholder')}")

        buttons = page.query_selector_all("button")
        for i, btn in enumerate(buttons):
            print(f"DEBUG button[{i}]: type={btn.get_attribute('type')} text={btn.inner_text()[:30]}")

        print("DEBUG: Filling login form")
        page.fill("#loginformemail", TMS_USERNAME)
        page.fill("#loginformpassword", TMS_PASSWORD)
        page.click('button[type="submit"]')

        page.wait_for_timeout(5000)
        print(f"DEBUG: URL after submit: {page.url}")

        error_el = page.query_selector('.alert, .error, [class*="error"], [class*="alert"], .toast, .toastr')
        if error_el:
            print(f"DEBUG: Login error message: {error_el.inner_text()[:200]}")

        if "login" not in page.url.lower():
            print("DEBUG: Login succeeded - URL changed")
        else:
            page.wait_for_load_state("networkidle", timeout=20000)
            print(f"DEBUG: URL after networkidle: {page.url}")
            if "login" in page.url.lower():
                error_texts = page.query_selector_all('[class*="error"], [class*="danger"], [class*="invalid"], .toast-error')
                for el in error_texts:
                    print(f"DEBUG error text: {el.inner_text()[:200]}")
                raise RuntimeError("Login failed - check TMS_USERNAME and TMS_PASSWORD credentials")

        print("DEBUG: Navigating to alarm page")
        page.goto(f"{TMS_BASE_URL}/alarm-monitoring", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=20000)

        if not captured.get("alarms"):
            page.goto(f"{TMS_BASE_URL}/rbe-alarm", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=20000)

        if not captured.get("alarms"):
            page.goto(f"{TMS_BASE_URL}/dashboard", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=20000)

        browser.close()

    alarms = captured.get("alarms", [])
    print(f"DEBUG: Captured {len(alarms)} alarms")
    return alarms


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

    raw_alarms = fetch_alarms_via_browser()
    payload = transform(raw_alarms)
    push_to_worker(payload)


if __name__ == "__main__":
    main()

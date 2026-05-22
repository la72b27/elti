"""Browser-based TMS login; captures the first alarm API request for token + headers."""

from __future__ import annotations
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, Page


def login_and_capture(base_url: str, username: str, password: str) -> dict:
    """
    1. Log in via headless Chromium.
    2. Navigate to the alarm page and trigger one 'Retrieve Active Alarms' click.
    3. Intercept the outgoing API request to capture:
       - api_base   : full endpoint URL (no query string)
       - token      : bearer token
       - ctx_headers: x-*-for context headers
       - base_params: SelectedLiftCompanyIds + selectedTownCouncilIds pairs
    4. Close browser and return the captured dict.

    The browser is only used long enough to get valid credentials; all subsequent
    data fetching is done via direct HTTP (no more per-page Playwright waits).
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        _do_login(page, base_url, username, password)

        print("Navigating to alarm page...")
        page.goto(f"{base_url}/lift/tms-lmd-alarm", wait_until="networkidle")
        page.wait_for_timeout(3000)

        captured = _trigger_and_capture(page)
        browser.close()

    if not captured:
        raise RuntimeError("Could not capture TMS API request — token interception failed")

    print(f"  api_base    : {captured['api_base']}")
    print(f"  ctx_headers : {list(captured['ctx_headers'].keys())}")
    print(f"  base_params : {captured['base_params']}")
    return captured


# ── helpers ────────────────────────────────────────────────────────────────────

def _do_login(page: Page, base_url: str, username: str, password: str) -> None:
    print(f"Logging in: {base_url}/login")
    page.goto(f"{base_url}/login", wait_until="networkidle")
    page.fill("#loginformemail", username)
    page.fill("#loginformpassword", password)
    page.click("button:has-text('Login'), button[type='submit']")
    page.wait_for_timeout(4000)
    print(f"  Login done. URL: {page.url}")


def _trigger_and_capture(page: Page) -> dict | None:
    """Select COMF alarm, click Retrieve, intercept the outgoing API request."""
    try:
        dropdown = page.wait_for_selector(
            "#tmsAlarm2, #tmsAlarm1, .alarm-select app-searchable-dropdown",
            timeout=10_000,
        )
        dropdown.click()
        inp = dropdown.query_selector("input[placeholder='Search']")
        inp.fill("COMF")
        page.wait_for_timeout(800)
        option = page.wait_for_selector("td:has-text('COMF')", timeout=5000)
        option.click()
        print("  Selected COMF from dropdown")
    except Exception as e:
        print(f"  WARN selecting dropdown: {e}")
        return None

    try:
        btn = page.wait_for_selector(
            "button:has-text('Retrieve Active Alarms')", timeout=10_000
        )
    except Exception as e:
        print(f"  WARN finding Retrieve button: {e}")
        return None

    # Intercept the first matching API request triggered by the button click
    try:
        with page.expect_request(
            lambda r: "retrieveTmsAlarms" in r.url, timeout=20_000
        ) as req_info:
            btn.click()
            print("  Clicked 'Retrieve Active Alarms'")
        req = req_info.value
    except Exception as e:
        print(f"  WARN intercepting request: {e}")
        return None

    return _parse_request(req)


def _parse_request(req) -> dict:
    """Extract token, context headers, and base params from an intercepted request."""
    auth = req.headers.get("authorization", "")
    token = auth.split("Bearer ", 1)[-1] if "Bearer " in auth else ""

    ctx_keys = ("x-cid-for", "x-gid-for", "x-tid-for", "x-uid-for")
    ctx_headers = {k: req.headers[k] for k in ctx_keys if k in req.headers}

    parsed = urlparse(req.url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    base_params: list[tuple[str, str]] = []
    for key in ("SelectedLiftCompanyIds", "selectedTownCouncilIds"):
        for v in qs.get(key, []):
            base_params.append((key, v))

    return {
        "api_base":    parsed.scheme + "://" + parsed.netloc + parsed.path,
        "token":       token,
        "ctx_headers": ctx_headers,
        "base_params": base_params,
        "origin":      f"{parsed.scheme}://{parsed.netloc}",
    }

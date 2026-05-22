"""Browser-based TMS login; captures the first alarm API request for token + headers."""

from __future__ import annotations
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, Page


def login_and_capture(base_url: str, username: str, password: str) -> dict:
    """
    1. Log in via headless Chromium.
    2. Navigate to the alarm page and capture the outgoing alarm API request via:
       - Layer 1: passive monitoring of auto-loaded requests on page load
       - Layer 2: try to interact with the alarm dropdown (multiple selectors)
       - Layer 3: click Retrieve button directly (with or without dropdown selection)
    3. Extract token, context headers, and base params from the captured request.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        _do_login(page, base_url, username, password)

        print("Navigating to alarm page...")
        captured: list = []

        def _on_req(req):
            if _is_alarm_request(req):
                captured.append(req)

        page.on("request", _on_req)
        page.goto(f"{base_url}/lift/tms-lmd-alarm", wait_until="networkidle")

        # Layer 1: page may auto-fire the alarm request on load
        page.wait_for_timeout(3000)
        if captured:
            print("  Captured auto-loaded request")
            result = _parse_request(captured[0])
            browser.close()
            _print_result(result)
            return result

        # Layer 2: try to select COMF from the dropdown
        _try_select_comf(page)

        # Layer 3: find and click Retrieve button, intercept the triggered request
        result = _click_retrieve_and_capture(page, captured)
        browser.close()

    if not result:
        raise RuntimeError("Could not capture TMS API request — token interception failed")

    _print_result(result)
    return result


# ── helpers ────────────────────────────────────────────────────────────────────

def _do_login(page: Page, base_url: str, username: str, password: str) -> None:
    print(f"Logging in: {base_url}/login")
    page.goto(f"{base_url}/login", wait_until="networkidle")

    for sel in ["#loginformemail", "input[type='email']", "input[name='email']",
                "input[placeholder*='email' i]", "input[placeholder*='user' i]"]:
        try:
            page.wait_for_selector(sel, timeout=3000)
            page.fill(sel, username)
            break
        except Exception:
            continue

    for sel in ["#loginformpassword", "input[type='password']", "input[name='password']"]:
        try:
            page.wait_for_selector(sel, timeout=3000)
            page.fill(sel, password)
            break
        except Exception:
            continue

    page.click("button:has-text('Login'), button[type='submit'], input[type='submit']")
    page.wait_for_timeout(5000)
    print(f"  Login done. URL: {page.url}")


def _is_alarm_request(req) -> bool:
    """Return True if this looks like the TMS alarm data API request."""
    if not req.headers.get("authorization"):
        return False
    if "retrieveTmsAlarms" in req.url:
        return True
    # Fallback: any authenticated GET with alarm-related params
    if req.method == "GET" and (
        "selectedAlarmCodes" in req.url
        or "SelectedLiftCompanyIds" in req.url
        or "tmsAlarm" in req.url.lower()
    ):
        return True
    return False


def _try_select_comf(page: Page) -> bool:
    """Try to select COMF from any alarm-type dropdown. Returns True on success."""
    dropdown_selectors = [
        "#tmsAlarm2",
        "#tmsAlarm1",
        ".alarm-select app-searchable-dropdown",
        "app-searchable-dropdown",
        "[id*='Alarm']",
        ".alarm-select",
    ]
    for sel in dropdown_selectors:
        try:
            dropdown = page.wait_for_selector(sel, timeout=3000)
            dropdown.click()
            page.wait_for_timeout(400)
            inp = (dropdown.query_selector("input[placeholder='Search']")
                   or page.query_selector("input[placeholder='Search']"))
            if inp:
                inp.fill("COMF")
                page.wait_for_timeout(800)
            for opt_sel in ["td:has-text('COMF')", "li:has-text('COMF')",
                            "[class*='option']:has-text('COMF')"]:
                opt = page.query_selector(opt_sel)
                if opt:
                    opt.click()
                    print(f"  Selected COMF via {sel}")
                    return True
        except Exception:
            continue
    print("  WARN: could not select COMF from dropdown, proceeding without selection")
    return False


def _click_retrieve_and_capture(page: Page, already_captured: list) -> dict | None:
    """Click the Retrieve button and capture the outgoing alarm request."""
    retrieve_selectors = [
        "button:has-text('Retrieve Active Alarms')",
        "button:has-text('Retrieve')",
        "button:has-text('Search')",
    ]
    btn = None
    for sel in retrieve_selectors:
        try:
            btn = page.wait_for_selector(sel, timeout=5000)
            break
        except Exception:
            continue

    if not btn:
        print("  WARN: Retrieve button not found")
        return _parse_request(already_captured[0]) if already_captured else None

    try:
        with page.expect_request(_is_alarm_request, timeout=20_000) as req_info:
            btn.click()
            print("  Clicked Retrieve button")
        return _parse_request(req_info.value)
    except Exception as e:
        print(f"  WARN intercepting request: {e}")
        return _parse_request(already_captured[0]) if already_captured else None


def _print_result(result: dict) -> None:
    print(f"  api_base    : {result['api_base']}")
    print(f"  ctx_headers : {list(result['ctx_headers'].keys())}")
    print(f"  base_params : {result['base_params']}")


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

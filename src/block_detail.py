"""Block detail page renderer for ELTI Worker (v1.4.0.4)."""

_VERSION = "1.4.0.4"

try:
    from urllib.parse import quote as _url_quote
except ImportError:
    def _url_quote(s, safe=""):  # type: ignore[misc]
        result = []
        safe_set = set(safe) | set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
        )
        for c in s:
            if c in safe_set:
                result.append(c)
            elif c == " ":
                result.append("%20")
            else:
                result.append(f"%{ord(c):02X}")
        return "".join(result)


# ── HTML template ─────────────────────────────────────────────────────────────

_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'self'; style-src 'unsafe-inline' https://cdn.jsdelivr.net; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'">
  <meta http-equiv="X-Content-Type-Options" content="nosniff">
  <title>ELTI – ###BLOCK_ID###</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background: #f0f2f5; padding: 20px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow-x: hidden; }
    .page-wrap { max-width: 720px; margin: auto; }
    .card { border-radius: 10px; box-shadow: 0 4px 16px rgba(0,0,0,.09); margin-bottom: 16px; overflow: hidden; }
    .card-header { border-radius: 10px 10px 0 0 !important; font-weight: 600; padding: 10px 16px; }
    .block-title { font-size: 1.6rem; font-weight: 700; color: #2a007c; letter-spacing: .02em; }
    .lmd-device-id { font-size: .82em; color: #888; font-family: monospace; white-space: nowrap; }
    .device-id-list { font-size: 1.07rem; font-weight: 700; color: #2a007c; letter-spacing: .02em; text-align: right; }
    .sub-addr { font-size: .9em; color: #555; border-bottom: 1px dashed #bbb; text-decoration: none; display: inline-block; margin-top: 4px; cursor: pointer; background: none; border-top: none; border-left: none; border-right: none; padding: 0; -webkit-tap-highlight-color: transparent; touch-action: manipulation; }
    .sub-addr:hover, .sub-addr:active { color: #2a007c; border-bottom-color: #2a007c; }
    .field-label { color: #888; font-size: .72em; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 2px; }
    .field-value { font-size: .95em; font-weight: 500; word-break: break-word; }
    .hdr-tms { background: #2a007c; color: #fff; }
    .hdr-lt  { background: rgb(34,213,254); color: #1a1a2e; }
    .bdg-comf { background: rgb(153,87,255); color: #fff; border-radius: 20px; padding: 2px 10px; font-size: .8em; font-weight: 500; display:inline-block; flex-shrink:0; }
    .bdg-iof  { background: rgb(34,213,254);  color: #222; border-radius: 20px; padding: 2px 10px; font-size: .8em; font-weight: 500; display:inline-block; flex-shrink:0; }
    .alarm-time { font-size: .95em; font-weight: 500; }
    .no-data { color: #999; font-style: italic; margin: 0; }
    .lt-left  { border-right: 1px solid #e9ecef; }
    .lt-divider { border: 0; border-top: 1px solid #e9ecef; margin: 10px 0 6px; }
    @media (max-width: 576px) {
      body { padding: 10px; }
      .block-title { font-size: 1.25rem; }
      .device-id-list { font-size: .83rem; }
      .lt-left { border-right: none; border-bottom: 1px solid #e9ecef; margin-bottom: 12px; padding-bottom: 4px; }
      /* Reduce header card side padding on narrow screens */
      .card-body.py-3.px-4 { padding-left: 1rem !important; padding-right: 1rem !important; }
    }
  </style>
</head>
<body>
<div class="page-wrap">

  <!-- Nav bar -->
  <div class="d-flex align-items-center justify-content-between mb-3">
    <span class="text-muted" style="font-size:.85em">
      ELTI Block Detail
      &nbsp;<span class="badge bg-secondary" style="font-size:.65em;vertical-align:middle">Updated: ###UPDATED###</span>
    </span>
    <a href="/" class="btn btn-sm btn-outline-secondary" style="-webkit-tap-highlight-color:transparent;touch-action:manipulation">← Back</a>
  </div>

  <!-- Header card: block ID + LMD Device ID + address -->
  <div class="card">
    <div class="card-body py-3 px-4">
      <div class="d-flex justify-content-between align-items-center mb-1">
        <div class="block-title">###BLOCK_ID###</div>
        ###LMD_DEVICE_ID_HTML###
      </div>
      ###ADDRESS_HTML###
    </div>
  </div>

  <!-- TMS alarm card -->
  ###ALARM_CARD###

  <!-- LMD INFO enrichment card -->
  ###LT_CARD###

</div>
<script>
async function openOneMap(block, address, el) {
  var sv = encodeURIComponent(block + ' ' + address);
  var api = '/api/onemap/search?searchVal=' + sv + '&returnGeom=Y&getAddrDetails=Y&pageNum=1';
  var orig = el.textContent;
  el.textContent = '⏳ ' + orig;
  el.style.pointerEvents = 'none';
  var ctrl = new AbortController();
  var tid = setTimeout(function(){ ctrl.abort(); }, 8000);
  try {
    var resp = await fetch(api, {signal: ctrl.signal});
    clearTimeout(tid);
    if (!resp.ok) throw new Error('http');
    var j = await resp.json();
    if (Array.isArray(j.results) && j.results.length > 0) {
      var r = j.results[0];
      var lat = parseFloat(r.LATITUDE), lng = parseFloat(r.LONGITUDE);
      if (isFinite(lat) && isFinite(lng)) {
        var u = new URL('https://www.onemap.gov.sg/main/v2/');
        u.searchParams.set('lat', lat.toFixed(6));
        u.searchParams.set('lng', lng.toFixed(6));
        u.searchParams.set('zoomLevel', '18');
        u.searchParams.set('marker', lat.toFixed(6)+','+lng.toFixed(6)+','+block+' '+address);
        window.open(u.toString(), '_blank');
        el.textContent = orig; el.style.pointerEvents = '';
        return;
      }
    }
    window.open('https://www.onemap.gov.sg/main/v2/?query=' + sv, '_blank');
  } catch(e) {
    clearTimeout(tid);
    window.open('https://www.onemap.gov.sg/main/v2/?query=' + sv, '_blank');
  }
  el.textContent = orig; el.style.pointerEvents = '';
}
</script>
</body>
</html>"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _esc(v) -> str:
    s = str(v) if v is not None else ""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def _js(v) -> str:
    """Escape for use inside a JS single-quoted string."""
    return _esc(str(v) if v is not None else "").replace("'", "&#39;")


def _field(label: str, value, col: str = "col-12") -> str:
    raw = str(value).strip() if value is not None else ""
    val_html = _esc(raw) if raw else "<span style='color:#ccc'>—</span>"
    return (
        f'<div class="{col} mb-2">'
        f'<div class="field-label">{label}</div>'
        f'<div class="field-value">{val_html}</div>'
        f'</div>'
    )


# ── Main render ───────────────────────────────────────────────────────────────

def render_html(rows: list, tc: str, pfx: str, block: str,
                last_updated: str = "") -> str:
    """Return a complete HTML page for a single block.

    Each dict in *rows* must contain the keys produced by _d1_load_block():
        tc, pfx, block, lift, address, postcode, lcoy, status_date,
        rbe, rbe_display, status,
        town_council, full_add, lt_postal_code, lift_names_all, interface, lss,
        lmd_device_id,
        lmd_ip, proxy_ip, vp_tun_ip, lmd_tun_ip, dvr_ip,
        lmd_devices  (list of per-device dicts)
    Rows with rbe='' are LT-only stub rows (no TMS alarm); alarm card skips them.
    """
    block_id = f"{_esc(tc)} {_esc(pfx)} {_esc(block)}"

    # ── Collect shared values from first available row ─────────────────────
    postcode = ""
    address  = ""
    for row in rows:
        postcode = postcode or (row.get("postcode") or "")
        address  = address  or (row.get("address")  or "")
        if postcode and address:
            break

    # ── Collect all unique LMD Device IDs from lmd_devices ────────────────
    all_device_ids: list = []
    _seen_ids: set = set()
    for row in rows:
        for dev in (row.get("lmd_devices") or []):
            did = dev.get("lmd_device_id") or ""
            if did and did not in _seen_ids:
                _seen_ids.add(did)
                all_device_ids.append(did)

    # ── Header: all LMD Device IDs (right side, 2/3 of block-title size) ──
    if all_device_ids:
        ids_inner = "".join(
            f'<div class="device-id-list">{_esc(d)}</div>'
            for d in all_device_ids
        )
        lmd_device_id_html = f'<div class="text-end">{ids_inner}</div>'
    else:
        lmd_device_id_html = ""

    # ── Header: address link ───────────────────────────────────────────────
    if address:
        pc_part = (f'&nbsp;&nbsp;<span style="color:#aaa">·</span>&nbsp;&nbsp;{_esc(postcode)}'
                   if postcode else "")
        address_html = (
            f'<button class="sub-addr" '
            f'onclick="openOneMap(\'{_js(block)}\',\'{_js(address)}\',this)">'
            f'{_esc(address)}{pc_part}'
            f'</button>'
        )
    else:
        address_html = (
            f'<span class="text-muted small">{_esc(postcode) or "No address data"}</span>'
        )

    # ── Merged TMS Alarm card: one row per RBE, badge + time only ─────────
    alarm_rows_html = ""
    for row in rows:
        rbe         = row.get("rbe", "")
        if not rbe:     # LT-only stub row — no TMS alarm
            continue
        rbe_display = row.get("rbe_display") or rbe
        bdg_cls     = "bdg-comf" if rbe == "COMF" else "bdg-iof"
        status_date = _esc(row.get("status_date") or "")
        time_html   = (status_date
                       if status_date
                       else "<span style='color:#ccc'>—</span>")
        alarm_rows_html += (
            f'<div class="d-flex align-items-center gap-2 mb-2">'
            f'<span class="{bdg_cls}">{_esc(rbe_display)}</span>'
            f'<span class="alarm-time">{time_html}</span>'
            f'</div>'
        )

    if alarm_rows_html:
        alarm_card = (
            '<div class="card">'
            '<div class="card-header hdr-tms">TMS Alarm</div>'
            f'<div class="card-body py-3">{alarm_rows_html}</div>'
            '</div>'
        )
    else:
        alarm_card = (
            '<div class="card">'
            '<div class="card-header hdr-tms">TMS Alarm</div>'
            '<div class="card-body">'
            '<p class="no-data">No TMS alarm record found for this block.</p>'
            '</div></div>'
        )

    # ── LMD INFO Enrichment card ──────────────────────────────────────────
    # Collect common LT data and per-device list from first matching rows
    lt_data     = None
    lmd_devices = []
    for row in rows:
        if lt_data is None and any(
            row.get(k) for k in ("town_council", "lift_names_all", "full_add", "interface")
        ):
            lt_data = row
        if not lmd_devices:
            lmd_devices = row.get("lmd_devices") or []
        if lt_data and lmd_devices:
            break

    has_lt = lt_data is not None

    # Section background colours: Part 1 neutral, then COMF-tint / IOF-tint / fallback
    _SECT_BG = ["#f8f9fa", "#f0eeff", "#e8fbff", "#f0fff4"]

    if has_lt or lmd_devices:
        # Part 1: common fields (full width, stacked)
        _bg0 = _SECT_BG[0]
        part1_html = (
            f'<div style="background:{_bg0};padding:12px 16px">'
            '<div class="row g-0">'
            '<div class="col-6 lt-left pe-3">'
            + _field("Town Council", (lt_data.get("town_council") or "") if has_lt else "")
            + _field("Full Address", (lt_data.get("full_add")      or "") if has_lt else "")
            + '</div>'
            '<div class="col-6 ps-3">'
            + _field("Lift Names",   (lt_data.get("lift_names_all") or "") if has_lt else "")
            + _field("Interface",    (lt_data.get("interface")       or "") if has_lt else "")
            + '</div>'
            '</div></div>'
        )

        # Part 2+: one section per LMD device, each with a distinct tinted background
        devices_html = ""
        for _i, dev in enumerate(lmd_devices):
            _bg = _SECT_BG[min(_i + 1, len(_SECT_BG) - 1)]
            left_html = (
                _field("Lift Name - Linked", dev.get("lift_name_linked") or "")
                + _field("LMD Device ID",    dev.get("lmd_device_id")    or "")
                + _field("LMD IP",           dev.get("lmd_ip")           or "")
                + _field("LSS",              dev.get("lss")              or "")
            )
            right_html = (
                _field("Proxy IP",   dev.get("proxy_ip")   or "")
                + _field("VP Tun IP",  dev.get("vp_tun_ip")  or "")
                + _field("LMD Tun IP", dev.get("lmd_tun_ip") or "")
                + _field("DVR IP",     dev.get("dvr_ip")     or "")
            )
            devices_html += (
                f'<div style="background:{_bg};padding:12px 16px;border-top:1px solid rgba(0,0,0,.07)">'
                '<div class="row g-0">'
                f'<div class="col-6 lt-left pe-3">{left_html}</div>'
                f'<div class="col-6 ps-3">{right_html}</div>'
                '</div></div>'
            )

        lt_card = (
            '<div class="card">'
            '<div class="card-header hdr-lt">LMD INFO Enrichment</div>'
            '<div class="card-body p-0">'
            + part1_html
            + devices_html
            + '</div></div>'
        )
    else:
        lt_card = (
            '<div class="card">'
            '<div class="card-header hdr-lt">LMD INFO Enrichment</div>'
            '<div class="card-body">'
            '<p class="no-data">No matching LMD INFO record found for this block.</p>'
            '</div></div>'
        )

    updated = _esc(last_updated) if last_updated else "—"

    html = _TEMPLATE
    html = html.replace("###BLOCK_ID###",          block_id)
    html = html.replace("###UPDATED###",           updated)
    html = html.replace("###LMD_DEVICE_ID_HTML###", lmd_device_id_html)
    html = html.replace("###ADDRESS_HTML###",       address_html)
    html = html.replace("###ALARM_CARD###",         alarm_card)
    html = html.replace("###LT_CARD###",            lt_card)
    return html

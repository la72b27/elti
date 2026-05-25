"""Block detail page renderer for ELTI Worker (v1.3.7.2)."""

_VERSION = "1.3.7.2"

try:
    from urllib.parse import quote as _url_quote
except ImportError:
    def _url_quote(s, safe=""):  # type: ignore[misc]
        result = []
        safe_set = set(safe) | set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~")
        for c in s:
            if c in safe_set:
                result.append(c)
            elif c == " ":
                result.append("%20")
            else:
                result.append(f"%{ord(c):02X}")
        return "".join(result)


# ── HTML template (###PLACEHOLDER### markers keep CSS braces intact) ──────────

_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'self'; style-src 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data:; frame-ancestors 'none'">
  <meta http-equiv="X-Content-Type-Options" content="nosniff">
  <title>ELTI – ###BLOCK_ID###</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background: #f0f2f5; padding: 20px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .page-wrap { max-width: 720px; margin: auto; }
    .card { border-radius: 10px; box-shadow: 0 4px 16px rgba(0,0,0,.09); margin-bottom: 16px; }
    .card-header { border-radius: 10px 10px 0 0 !important; font-weight: 600; padding: 10px 16px; }
    .block-title { font-size: 1.6rem; font-weight: 700; color: #2a007c; letter-spacing: .02em; }
    .sub-addr { font-size: .9em; color: #555; border-bottom: 1px dashed #bbb; text-decoration: none; display: inline-block; margin-top: 4px; }
    .sub-addr:hover { color: #2a007c; border-bottom-color: #2a007c; }
    .field-label { color: #888; font-size: .72em; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 2px; }
    .field-value { font-size: .95em; font-weight: 500; word-break: break-word; }
    .hdr-tms { background: #2a007c; color: #fff; }
    .hdr-lt  { background: #0d6efd; color: #fff; }
    .bdg-comf { background: rgb(153,87,255); color: #fff; border-radius: 20px; padding: 2px 10px; font-size: .8em; font-weight: 500; display:inline-block; }
    .bdg-iof  { background: rgb(34,213,254);  color: #222; border-radius: 20px; padding: 2px 10px; font-size: .8em; font-weight: 500; display:inline-block; }
    .status-set { background: #dc3545; color: #fff; border-radius: 4px; padding: 2px 7px; font-size: .85em; font-weight: bold; }
    .status-ok  { color: #28a745; font-weight: 500; }
    .no-data { color: #999; font-style: italic; margin: 0; }
    @media (max-width: 576px) { body { padding: 10px; } .block-title { font-size: 1.25rem; } }
  </style>
</head>
<body>
<div class="page-wrap">

  <!-- Nav bar -->
  <div class="d-flex align-items-center justify-content-between mb-3">
    <span class="text-muted" style="font-size:.85em">
      ELTI Block Detail
      &nbsp;<span class="badge bg-secondary" style="font-size:.65em;vertical-align:middle">v###VERSION###</span>
    </span>
    <a href="/" class="btn btn-sm btn-outline-secondary">← Back</a>
  </div>

  <!-- Header card: block ID + address -->
  <div class="card">
    <div class="card-body py-3 px-4">
      <div class="block-title mb-1">###BLOCK_ID###</div>
      ###ADDRESS_HTML###
    </div>
  </div>

  <!-- TMS alarm cards (one per RBE) -->
  ###ALARM_CARDS###

  <!-- Lift Talk enrichment card -->
  ###LT_CARD###

</div>
</body>
</html>"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _esc(v) -> str:
    s = str(v) if v is not None else ""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def _field(label: str, value, col: str = "col-6 col-sm-4") -> str:
    raw = str(value).strip() if value is not None else ""
    val_html = _esc(raw) if raw else "<span style='color:#ccc'>—</span>"
    return (
        f'<div class="{col} mb-3">'
        f'<div class="field-label">{label}</div>'
        f'<div class="field-value">{val_html}</div>'
        f'</div>'
    )


# ── Main render ───────────────────────────────────────────────────────────────

def render_html(rows: list, tc: str, pfx: str, block: str) -> str:
    """Return a complete HTML page for a single block.

    Each dict in *rows* must contain the keys produced by _d1_load_block():
        tc, pfx, block, lift, address, postcode, lcoy, status_date,
        rbe, rbe_display, status,
        town_council, full_add, lt_postal_code, lift_names_all, interface, lss
    """
    block_id = f"{_esc(tc)} {_esc(pfx)} {_esc(block)}"

    # ── Header: first available address / postcode ────────────────────────
    postcode = ""
    address  = ""
    for row in rows:
        postcode = postcode or (row.get("postcode") or "")
        address  = address  or (row.get("address")  or "")
        if postcode and address:
            break

    if address:
        q = _url_quote(f"{block} {address}")
        pc_part = f'&nbsp;&nbsp;<span style="color:#aaa">·</span>&nbsp;&nbsp;{_esc(postcode)}' if postcode else ""
        address_html = (
            f'<a class="sub-addr" '
            f'href="https://www.onemap.gov.sg/main/v2/?query={q}" '
            f'target="_blank" rel="noopener noreferrer">'
            f'{_esc(address)}{pc_part}'
            f'</a>'
        )
    else:
        address_html = f'<span class="text-muted small">{_esc(postcode) or "No address data"}</span>'

    # ── TMS Alarm cards ───────────────────────────────────────────────────
    alarm_parts = []
    for row in rows:
        rbe         = row.get("rbe", "")
        rbe_display = row.get("rbe_display") or rbe
        bdg_cls     = "bdg-comf" if rbe == "COMF" else "bdg-iof"
        try:
            status = int(row.get("status") or 1)
        except (TypeError, ValueError):
            status = 1
        status_html = ('<span class="status-set">SET</span>'
                       if status != 1 else '<span class="status-ok">Normal</span>')

        alarm_parts.append(
            '<div class="card">'
            f'<div class="card-header hdr-tms d-flex align-items-center gap-2">'
            f'TMS Alarm&nbsp;<span class="{bdg_cls}">{_esc(rbe_display)}</span>'
            '</div>'
            '<div class="card-body"><div class="row">'
            + _field("TC",          row.get("tc"))
            + _field("Pfx",         row.get("pfx"))
            + _field("Block",       row.get("block"))
            + _field("Lift",        row.get("lift"))
            + _field("LCOY",        row.get("lcoy"))
            + _field("Postcode",    row.get("postcode"))
            + _field("Status Date", row.get("status_date"), "col-12 col-sm-4")
            + (f'<div class="col-6 col-sm-4 mb-3">'
               f'<div class="field-label">Status</div>'
               f'<div class="field-value">{status_html}</div></div>')
            + '</div></div></div>'
        )

    alarm_cards = "\n".join(alarm_parts) if alarm_parts else (
        '<div class="card">'
        '<div class="card-header hdr-tms">TMS Alarm</div>'
        '<div class="card-body">'
        '<p class="no-data">No TMS alarm record found for this block.</p>'
        '</div></div>'
    )

    # ── Lift Talk enrichment card ─────────────────────────────────────────
    lt_data = None
    for row in rows:
        if any(row.get(k) for k in ("town_council", "lift_names_all", "full_add", "lss")):
            lt_data = row
            break

    if lt_data:
        lt_card = (
            '<div class="card">'
            '<div class="card-header hdr-lt">Lift Talk Enrichment</div>'
            '<div class="card-body"><div class="row">'
            + _field("Town Council",     lt_data.get("town_council"),    "col-12 col-sm-8")
            + _field("Postal Code (LT)", lt_data.get("lt_postal_code"),  "col-6 col-sm-4")
            + _field("Full Address",     lt_data.get("full_add"),         "col-12")
            + _field("Lift Names",       lt_data.get("lift_names_all"),   "col-12 col-sm-4")
            + _field("Interface",        lt_data.get("interface"),         "col-6 col-sm-4")
            + _field("LSS",              lt_data.get("lss"),               "col-6 col-sm-4")
            + '</div></div></div>'
        )
    else:
        lt_card = (
            '<div class="card">'
            '<div class="card-header hdr-lt">Lift Talk Enrichment</div>'
            '<div class="card-body">'
            '<p class="no-data">No matching Lift Talk record found for this block.</p>'
            '</div></div>'
        )

    html = _TEMPLATE
    html = html.replace("###BLOCK_ID###",     block_id)
    html = html.replace("###VERSION###",      _VERSION)
    html = html.replace("###ADDRESS_HTML###", address_html)
    html = html.replace("###ALARM_CARDS###",  alarm_cards)
    html = html.replace("###LT_CARD###",      lt_card)
    return html

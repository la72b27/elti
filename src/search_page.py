"""Block search page renderer for ELTI Worker (v1.4.0.4)."""

_VERSION = "1.4.0.4"

_SEARCH_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'self'; style-src 'unsafe-inline' https://cdn.jsdelivr.net; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'">
  <meta http-equiv="X-Content-Type-Options" content="nosniff">
  <title>ELTI – Block Search</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background: #f0f2f5; padding: 20px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow-x: hidden; }
    .page-wrap { max-width: 720px; margin: auto; }
    .card { border-radius: 10px; box-shadow: 0 4px 16px rgba(0,0,0,.09); margin-bottom: 16px; overflow: hidden; }
    .card-header { border-radius: 10px 10px 0 0 !important; font-weight: 600; padding: 10px 16px; }
    .block-title { font-size: 1.6rem; font-weight: 700; color: #2a007c; letter-spacing: .02em; }
    .lmd-device-id { font-size: .82em; color: #888; font-family: monospace; white-space: nowrap; }
    .device-id-list { font-size: 1.07rem; font-weight: 700; color: #2a007c; letter-spacing: .02em; text-align: right; }
    .field-label { color: #888; font-size: .72em; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 2px; }
    .field-value { font-size: .95em; font-weight: 500; word-break: break-word; }
    .hdr-tms  { background: #2a007c; color: #fff; }
    .hdr-lt   { background: rgb(34,213,254); color: #1a1a2e; }
    .hdr-srch { background: #2a007c; color: #fff; }
    .bdg-comf { background: rgb(153,87,255); color: #fff; border-radius: 20px; padding: 2px 10px; font-size: .8em; font-weight: 500; display:inline-block; flex-shrink:0; }
    .bdg-iof  { background: rgb(34,213,254);  color: #222; border-radius: 20px; padding: 2px 10px; font-size: .8em; font-weight: 500; display:inline-block; flex-shrink:0; }
    .alarm-time { font-size: .95em; font-weight: 500; }
    .no-data { color: #999; font-style: italic; margin: 0; }
    .lt-left  { border-right: 1px solid #e9ecef; }
    .lt-divider { border: 0; border-top: 1px solid #e9ecef; margin: 10px 0 6px; }
    .mode-btn { cursor: pointer; padding: 4px 14px; border-radius: 20px; font-size: .85em;
                font-weight: 600; border: 2px solid #2a007c; color: #2a007c; background: #fff;
                transition: all .2s; -webkit-tap-highlight-color: transparent;
                touch-action: manipulation; flex-shrink: 0; }
    .mode-btn.active { background: #2a007c; color: #fff; }
    .btn-srch { background: #2a007c; color: #fff; border: none; border-radius: 6px;
                padding: 8px 24px; font-weight: 600; font-size: .95em; cursor: pointer;
                transition: background .2s; -webkit-tap-highlight-color: transparent;
                touch-action: manipulation; -webkit-appearance: none; }
    .btn-srch:hover, .btn-srch:active { background: rgb(153,87,255); }
    .btn-open { background: #2a007c; color: #fff !important; border: none; border-radius: 6px;
                padding: 5px 16px; font-size: .85em; font-weight: 600; text-decoration: none;
                display: inline-block; transition: background .2s;
                -webkit-tap-highlight-color: transparent; touch-action: manipulation; }
    .btn-open:hover, .btn-open:active { background: rgb(153,87,255); }
    @media (max-width: 576px) {
      body { padding: 10px; }
      .block-title { font-size: 1.25rem; }
      .device-id-list { font-size: .83rem; }
      .lt-left { border-right: none; border-bottom: 1px solid #e9ecef; margin-bottom: 12px; padding-bottom: 4px; }
      /* Prevent iOS Safari from zooming in on input focus (requires ≥16px) */
      .form-control, .form-control-sm, input, select, textarea { font-size: 16px !important; }
      /* Mode toggle row wrap on very narrow screens */
      .d-flex.gap-2.mb-3 { flex-wrap: wrap; }
    }
  </style>
</head>
<body>
<div class="page-wrap">

  <!-- Nav -->
  <div class="d-flex align-items-center justify-content-between mb-3">
    <span class="text-muted" style="font-size:.85em">ELTI Block Search</span>
    <a href="/" class="btn btn-sm btn-outline-secondary" style="-webkit-tap-highlight-color:transparent;touch-action:manipulation">← Back</a>
  </div>

  <!-- Search card -->
  <div class="card">
    <div class="card-header hdr-srch">Search Block</div>
    <div class="card-body">

      <!-- Mode toggle -->
      <div class="d-flex gap-2 mb-3">
        <button class="mode-btn active" id="btnModeBlock" onclick="setMode('block')">TC / Pfx / Block</button>
        <button class="mode-btn"        id="btnModePC"    onclick="setMode('pc')">Postcode</button>
      </div>

      <!-- TC / Pfx / Block form -->
      <div id="formBlock">
        <div class="row g-2 mb-2">
          <div class="col-4">
            <div class="field-label mb-1">TC</div>
            <input id="inp-tc" class="form-control form-control-sm"
                   placeholder="e.g. JE" maxlength="6" autocomplete="off"
                   style="text-transform:uppercase">
          </div>
          <div class="col-3">
            <div class="field-label mb-1">Pfx</div>
            <input id="inp-pfx" class="form-control form-control-sm"
                   placeholder="e.g. B" maxlength="4" autocomplete="off"
                   style="text-transform:uppercase">
          </div>
          <div class="col-5">
            <div class="field-label mb-1">Block</div>
            <input id="inp-block" class="form-control form-control-sm"
                   placeholder="e.g. 296C" maxlength="10" autocomplete="off"
                   style="text-transform:uppercase">
          </div>
        </div>
      </div>

      <!-- Postcode form -->
      <div id="formPC" style="display:none">
        <div class="field-label mb-1">Postcode (6 digits)</div>
        <input id="inp-pc" class="form-control form-control-sm"
               placeholder="e.g. 670510" maxlength="6" inputmode="numeric"
               pattern="[0-9]{6}" autocomplete="off">
      </div>

      <div class="d-grid mt-3"><button class="btn-srch" onclick="doSearch()">Search</button></div>
    </div>
  </div>

  <!-- Results -->
  <div id="results"></div>

</div>
<script>
var currentMode = 'block';

function setMode(m) {
  currentMode = m;
  document.getElementById('btnModeBlock').classList.toggle('active', m === 'block');
  document.getElementById('btnModePC').classList.toggle('active', m === 'pc');
  document.getElementById('formBlock').style.display = m === 'block' ? '' : 'none';
  document.getElementById('formPC').style.display    = m === 'pc'    ? '' : 'none';
}

function esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fld(label, val) {
  var v = val && String(val).trim() ? esc(val) : '<span style="color:#ccc">—</span>';
  return '<div class="col-12 mb-2"><div class="field-label">' + label +
         '</div><div class="field-value">' + v + '</div></div>';
}

function renderResults(d) {
  if (!d.found) {
    document.getElementById('results').innerHTML =
      '<div class="alert alert-warning mt-0">' + esc(d.message || 'No matching block found.') + '</div>';
    return;
  }

  // ── Header card ──────────────────────────────────────────────────────────
  var devIds = [], seenDevIds = {};
  if (Array.isArray(d.lmd_devices)) {
    d.lmd_devices.forEach(function(dev) {
      var id = dev.lmd_device_id;
      if (id && !seenDevIds[id]) { seenDevIds[id] = true; devIds.push(id); }
    });
  }
  var devIdHtml = devIds.length
    ? '<div class="text-end">' + devIds.map(function(id) {
        return '<div class="device-id-list">' + esc(id) + '</div>';
      }).join('') + '</div>'
    : '';
  var html = '<div class="card"><div class="card-body py-3 px-4">'
    + '<div class="d-flex justify-content-between align-items-center mb-1">'
    + '<div class="block-title">' + esc(d.block_id) + '</div>'
    + devIdHtml
    + '</div>';
  if (d.address || d.postcode) {
    html += '<div class="text-muted small">' + esc(d.address || d.postcode) + '</div>';
  }
  html += '</div></div>';

  // ── TMS Alarm card ────────────────────────────────────────────────────────
  var alarmBody = '';
  if (d.alarms && d.alarms.length) {
    d.alarms.forEach(function(a) {
      var cls = a.rbe === 'COMF' ? 'bdg-comf' : 'bdg-iof';
      var t   = a.status_date ? esc(a.status_date) : '<span style="color:#ccc">—</span>';
      alarmBody += '<div class="d-flex align-items-center gap-2 mb-2">'
        + '<span class="' + cls + '">' + esc(a.rbe_display || a.rbe) + '</span>'
        + '<span class="alarm-time">' + t + '</span></div>';
    });
  } else {
    alarmBody = '<p class="no-data">No TMS alarm record found for this block.</p>';
  }
  html += '<div class="card"><div class="card-header hdr-tms">TMS Alarm</div>'
        + '<div class="card-body py-3">' + alarmBody + '</div></div>';

  // ── LMD INFO Enrichment card ──────────────────────────────────────────────
  var lt      = d.lt || {};
  var devices = Array.isArray(d.lmd_devices) ? d.lmd_devices : [];
  var hasLT   = [lt.town_council, lt.full_add, lt.lift_names_all, lt.interface].some(function(v){return v && v.trim();});
  // Section bg: Part1 neutral, then COMF-tint, IOF-tint, fallback
  var sectBg = ['#f8f9fa', '#f0eeff', '#e8fbff', '#f0fff4'];

  if (hasLT || devices.length) {
    // Part 1: two equal columns – left: Town Council + Full Address, right: Lift Names + Interface
    var part1 = '<div style="background:' + sectBg[0] + ';padding:12px 16px">'
      + '<div class="row g-0">'
      + '<div class="col-6 lt-left pe-3">'
      + fld('Town Council', lt.town_council) + fld('Full Address', lt.full_add)
      + '</div>'
      + '<div class="col-6 ps-3">'
      + fld('Lift Names', lt.lift_names_all) + fld('Interface', lt.interface)
      + '</div>'
      + '</div></div>';

    // Part 2+: one section per LMD device, each with a distinct tinted background
    var devSections = '';
    devices.forEach(function(dev, i) {
      var bg = sectBg[Math.min(i + 1, sectBg.length - 1)];
      var left = fld('Lift Name - Linked', dev.lift_name_linked)
               + fld('LMD Device ID',     dev.lmd_device_id)
               + fld('LMD IP',            dev.lmd_ip)
               + fld('LSS',               dev.lss);
      var right= fld('Proxy IP',   dev.proxy_ip)
               + fld('VP Tun IP',  dev.vp_tun_ip)
               + fld('LMD Tun IP', dev.lmd_tun_ip)
               + fld('DVR IP',     dev.dvr_ip);
      devSections += '<div style="background:' + bg + ';padding:12px 16px;border-top:1px solid rgba(0,0,0,.07)">'
        + '<div class="row g-0">'
        + '<div class="col-6 lt-left pe-3">' + left  + '</div>'
        + '<div class="col-6 ps-3">'          + right + '</div>'
        + '</div></div>';
    });

    html += '<div class="card"><div class="card-header hdr-lt">LMD INFO Enrichment</div>'
          + '<div class="card-body p-0">' + part1 + devSections + '</div></div>';
  } else {
    html += '<div class="card"><div class="card-header hdr-lt">LMD INFO Enrichment</div>'
          + '<div class="card-body"><p class="no-data">No matching LMD INFO record found for this block.</p>'
          + '</div></div>';
  }

  document.getElementById('results').innerHTML = html;
}

async function doSearch() {
  var url;
  if (currentMode === 'pc') {
    var pc = document.getElementById('inp-pc').value.trim();
    if (!/^\d{6}$/.test(pc)) {
      document.getElementById('results').innerHTML =
        '<div class="alert alert-warning mt-0">Please enter a valid 6-digit postcode.</div>';
      return;
    }
    url = '/api/search?postcode=' + encodeURIComponent(pc);
  } else {
    var tc  = document.getElementById('inp-tc').value.trim().toUpperCase();
    var pfx = document.getElementById('inp-pfx').value.trim().toUpperCase();
    var blk = document.getElementById('inp-block').value.trim().toUpperCase();
    if (!tc || !blk) {
      document.getElementById('results').innerHTML =
        '<div class="alert alert-warning mt-0">TC and Block are required.</div>';
      return;
    }
    url = '/api/search?tc=' + encodeURIComponent(tc)
        + '&pfx=' + encodeURIComponent(pfx)
        + '&block=' + encodeURIComponent(blk);
  }

  document.getElementById('results').innerHTML =
    '<div class="text-center text-muted py-3" style="font-size:.9em">Searching…</div>';

  try {
    var resp = await fetch(url);
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    renderResults(await resp.json());
  } catch(e) {
    document.getElementById('results').innerHTML =
      '<div class="alert alert-danger mt-0">Error: ' + esc(e.message) + '</div>';
  }
}

// Enter key triggers search
document.addEventListener('keydown', function(e) {
  if (e.key === 'Enter') doSearch();
});

// Auto-search from URL params on page load
(function() {
  var p = new URLSearchParams(location.search);
  var pc = p.get('postcode'), tc = p.get('tc'), blk = p.get('block');
  if (pc) {
    setMode('pc');
    document.getElementById('inp-pc').value = pc;
    doSearch();
  } else if (tc && blk) {
    setMode('block');
    document.getElementById('inp-tc').value    = tc.toUpperCase();
    document.getElementById('inp-pfx').value   = (p.get('pfx') || '').toUpperCase();
    document.getElementById('inp-block').value = blk.toUpperCase();
    doSearch();
  }
})();
</script>
</body>
</html>"""


def render_html() -> str:
    return _SEARCH_TEMPLATE

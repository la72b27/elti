from js import Response, Headers, fetch, Object
import json
import onemap
import block_detail

VERSION = "1.3.7.2"

# Base64 encoded logo
LOGO_BASE64 = "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"

# 完整的 HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'unsafe-inline' https://cdn.jsdelivr.net; connect-src 'self' https://www.onemap.gov.sg https://cdn.jsdelivr.net; img-src 'self' data: https://*.tile.openstreetmap.org https://www.onemap.gov.sg; frame-ancestors 'none'">
    <meta http-equiv="X-Content-Type-Options" content="nosniff">
    <meta name="referrer" content="strict-origin-when-cross-origin">
    <title>ELTI - EP1W LMD Telemetry Insight</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root { 
            --comf-color: rgb(153, 87, 255); 
            --iof-color: rgb(34, 213, 254);
            --insight-color: rgb(176, 244, 43);
            --theme-color: var(--comf-color); 
        }
        body { background-color: #f0f2f5; padding: 15px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow-x: hidden; }
        .container-fluid { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1); width: 100%; max-width: 1400px; margin: auto; position: relative; }

        /* --- Top bar: Logo + Cloud Sync row --- */
        .header-top { display: flex; align-items: stretch; justify-content: space-between; gap: 12px; margin-bottom: 12px; width: 100%; }
        .logo-container { display: flex; align-items: center; flex-shrink: 0; }
        .logo-img { height: 90px; width: auto; object-fit: contain; display: block; }
        .filter-info-inline { display: flex; flex-direction: column; justify-content: center; font-size: 0.7em; background: #f8f9fa; padding: 8px 12px; border-radius: 8px; border-left: 4px solid rgb(42, 0, 124); line-height: 1.3; flex-grow: 1; }
        .filter-info-inline strong { color: rgb(42, 0, 124); font-size: 0.9em; margin-bottom: 3px; display: block; }
        .filter-info-inline div { margin-bottom: 2px; white-space: nowrap; }

        /* --- Button row: COMF / IOF --- */
        .header-btns { display: flex; gap: 8px; align-items: center; margin-bottom: 15px; }
        .btn-stat { padding: 4px 14px; height: 38px; font-size: 0.95em; font-weight: bold; border-radius: 6px; transition: all 0.3s; border: 2px solid var(--comf-color); background-color: #fff; color: var(--comf-color); white-space: nowrap; display: flex; align-items: center; }
        .btn-stat.btn-iof-toggle { border-color: var(--iof-color); color: var(--iof-color); }
        .btn-stat.btn-comf-toggle.active, .btn-stat.btn-comf-toggle:hover { background-color: var(--comf-color); color: #fff; border-color: var(--comf-color); }
        .btn-stat.btn-iof-toggle.active, .btn-stat.btn-iof-toggle:hover { background-color: var(--iof-color); color: #fff; border-color: var(--iof-color); }

        /* --- TC filter bar --- */
        .tc-stats { display: flex; gap: 8px; align-items: center; margin-bottom: 15px; flex-wrap: wrap; padding: 8px; background: #f8f9fa; border-radius: 8px; }
        .btn-tc { padding: 3px 10px; font-size: 0.85em; border: 1px solid #6c757d; background: #fff; color: #6c757d; transition: all 0.3s; white-space: nowrap; border-radius: 4px; }
        .btn-tc:hover, .btn-tc.active { background-color: var(--theme-color); color: #fff; border-color: var(--theme-color); }

        /* --- Table --- */
        .table-container { width: 100%; margin-bottom: 20px; overflow-x: auto; -webkit-overflow-scrolling: touch; border: 1px solid #dee2e6; border-radius: 8px; }
        table { font-size: 0.82em; width: 100%; table-layout: auto; border-collapse: collapse; margin-bottom: 0 !important; }
        th { background-color: var(--theme-color) !important; color: white !important; white-space: nowrap; text-align: center; padding: 0 !important; transition: background-color 0.3s; vertical-align: middle !important; position: sticky; top: 0; z-index: 10; }
        .sort-btn, .header-text { background: none; border: none; color: inherit; font: inherit; width: 100%; height: 100%; padding: 10px 6px; display: flex; align-items: center; justify-content: center; gap: 4px; margin: 0; }
        .sort-btn { cursor: pointer; }
        .sort-btn:hover { background-color: rgba(255,255,255,0.1); }
        .sort-btn::after { content: '↕'; font-size: 0.75em; opacity: 0.5; }
        .sort-btn.asc::after { content: '↑'; opacity: 1; }
        .sort-btn.desc::after { content: '↓'; opacity: 1; }
        td { white-space: nowrap; padding: 8px; vertical-align: middle; border: 1px solid #dee2e6; }
        .alarm-row:nth-child(even) { background-color: #f8f9fa; }
        .status-set { background-color: #dc3545; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.9em; }

        /* --- Responsive --- */
        @media (max-width: 992px) {
            .filter-info-inline div { white-space: normal; }
        }
        @media (max-width: 768px) {
            body { padding: 10px; }
            .container-fluid { padding: 12px; }
            .logo-img { height: 72px; }
            .header-btns { flex-wrap: wrap; }
            .btn-stat { padding: 3px 10px; height: 34px; font-size: 0.88em; }
        }
        @media (max-width: 576px) {
            body { padding: 6px; }
            .container-fluid { padding: 8px 8px; }
            .header-top { flex-direction: column; gap: 8px; }
            .logo-container { justify-content: flex-start; }
            .logo-img { height: 56px; }
            .filter-info-inline { font-size: 0.65em; padding: 6px 10px; }
            .filter-info-inline strong { font-size: 0.95em; }
            .header-btns { gap: 5px; margin-bottom: 10px; flex-wrap: wrap; }
            .btn-stat { flex: 1 0 auto; padding: 3px 8px; height: 32px; font-size: 0.82em; min-width: 0; white-space: nowrap; }
            .tc-stats { gap: 5px; padding: 6px; margin-bottom: 10px; }
            .btn-tc { font-size: 0.78em; padding: 2px 7px; }
            table { font-size: 0.76em; }
            td { padding: 6px 4px; }
            .sort-btn, .header-text { padding: 8px 4px; }
        }
        @media (max-width: 400px) {
            .logo-img { height: 46px; }
            .btn-stat { font-size: 0.74em; padding: 2px 6px; height: 30px; }
        }
        .btn-route-toggle { border-color: rgb(175, 245, 45); color: rgb(60, 100, 0); }
        .btn-route-toggle:hover { background-color: rgb(175, 245, 45); color: #222; border-color: rgb(175, 245, 45); }
        input[type="checkbox"].exclude-radio { cursor:pointer; width:15px; height:15px; accent-color:#dc3545; vertical-align:middle; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="header-top">
            <div class="logo-container">
                <img src="data:image/jpeg;base64,{{LOGO_BASE64}}" alt="Logo" class="logo-img">
            </div>
            <div class="filter-info-inline">
                <strong>Cloud Sync Active</strong>
                <div>Hardware: <span class="badge bg-dark">EP1WM</span></div>
                <div>Version: <span class="badge bg-info">""" + VERSION + """</span></div>
                <div>Updated: <span class="badge bg-secondary" id="updateTime">Never</span></div>
            </div>
        </div>
        <div class="header-btns">
            <button class="btn btn-stat btn-comf-toggle active" id="comfBtn">COMF 0/0</button>
            <button class="btn btn-stat btn-iof-toggle" id="iofBtn">IOF 0/0</button>
            <button class="btn btn-stat btn-route-toggle" id="routeBtn">Route 0/0</button>
        </div>

        <div class="tc-stats" id="tcContainer"></div>
        <div class="table-container">
            <table class="table table-hover table-bordered">
                <thead>
                    <tr>
                        <th><div class="header-text">No.</div></th>
                        <th><button class="sort-btn" onclick="sortByExclude(this)" title="Sort: masked rows to top">Mask</button></th>
                        <th><button class="sort-btn" onclick="sortTable(1, this)">Postcode</button></th>
                        <th><button class="sort-btn" onclick="sortTable(2, this)">TC</button></th>
                        <th><button class="sort-btn" onclick="sortTable(3, this)">Pfx</button></th>
                        <th><button class="sort-btn" onclick="sortTable(4, this)">Block</button></th>
                        <th><div class="header-text">Lift</div></th>
                        <th><div class="header-text">Address</div></th>
                        <th><div class="header-text">LCOY</div></th>
                        <th><button class="sort-btn" onclick="sortTable(8, this)">Status Date</button></th>
                        <th><div class="header-text">RBE</div></th>
                    </tr>
                </thead>
                <tbody id="tableBody"></tbody>
            </table>
        </div>
    </div>
    <script>
        const data = {{DATA_JSON}};
        // Initialize original index for sorting
        data.records.forEach((r, i) => r._index = i + 1);

        // 确保 Status Date 时间部分零补位，兼容所有日期格式
        // 例如 "14 May 2026 13:4" → "14 May 2026 13:40"
        //      "2026-05-14 9:3"   → "2026-05-14 09:03"
        function fmtDate(s) {
            if (!s || typeof s !== 'string' || s === '-') return s;
            const m = s.match(/^(.+)\s+(\d{1,2}):(\d{1,2})$/);
            if (m) return m[1] + ' ' + m[2].padStart(2,'0') + ':' + m[3].padStart(2,'0');
            return s;
        }
        
        let currentRBE = 'COMF';
        let currentTC = 'ALL';
        let sortDirections = {};
        const EXCLUDE_PC_KEY = 'elti_excluded_pc';
        // Server-side mask (KV-backed, cross-device authoritative)
        const _serverMask = {{MASK_JSON}};
        let excludedPostcodes = new Set(_serverMask);
        // If server has no masks yet, migrate from localStorage (one-time, first use)
        if (_serverMask.length === 0) {
            try {
                const _stored = localStorage.getItem(EXCLUDE_PC_KEY);
                const _parsed = JSON.parse(_stored || '[]');
                if (Array.isArray(_parsed) && _parsed.length > 0) {
                    excludedPostcodes = new Set(_parsed);
                    saveMask(); // push local data to server silently
                }
            } catch(e) {}
        }

        function updateBadges() {
            let comfEx = 0, iofEx = 0;
            data.records.forEach(r => {
                const pc = (r.Postcode || '').trim();
                if (!pc || pc === '-' || !excludedPostcodes.has(pc)) return;
                if (r.RBE === 'COMF') comfEx++;
                else if (r.RBE === 'IOF') iofEx++;
            });
            const comfCur = data.comf_count - comfEx;
            const iofCur = data.iof_count - iofEx;
            document.getElementById('comfBtn').textContent = `COMF ${comfCur}/${data.comf_count}`;
            document.getElementById('iofBtn').textContent = `IOF ${iofCur}/${data.iof_count}`;
            document.getElementById('routeBtn').textContent = `Route ${comfCur + iofCur}/${data.comf_count + data.iof_count}`;
        }

        async function saveMask() {
            const arr = [...excludedPostcodes];
            // localStorage: local resilience
            if (arr.length > 0) {
                localStorage.setItem(EXCLUDE_PC_KEY, JSON.stringify(arr));
            } else {
                localStorage.removeItem(EXCLUDE_PC_KEY);
            }
            // KV: cross-device sync (fire-and-forget)
            try {
                await fetch('/api/mask', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(arr)
                });
            } catch(e) { /* server sync failed; localStorage copy preserved */ }
        }

        function render() {
            // 强制截断时间，确保只显示 年-月-日 时:分
            let updatedStr = data.last_updated || "Never";
            if (updatedStr.includes(" ")) {
                let parts = updatedStr.split(" ");
                let timeParts = parts[1].split(":");
                updatedStr = parts[0] + " " + timeParts[0] + ":" + timeParts[1];
            }
            document.getElementById('updateTime').textContent = updatedStr;
            
            const tcContainer = document.getElementById('tcContainer');
            const stats = data.tc_stats[currentRBE] || {};
            tcContainer.innerHTML = '';
            const allBtn = document.createElement('button');
            allBtn.className = `btn btn-tc ${currentTC === 'ALL' ? 'active' : ''}`;
            allBtn.textContent = 'ALL';
            allBtn.onclick = () => setTC('ALL');
            tcContainer.appendChild(allBtn);
            Object.keys(stats).sort().forEach(tc => {
                const btn = document.createElement('button');
                btn.className = `btn btn-tc ${currentTC === tc ? 'active' : ''}`;
                btn.textContent = `${tc} ${stats[tc]}`;
                btn.onclick = () => setTC(tc);
                tcContainer.appendChild(btn);
            });

            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';

            // Filter records first
            let filteredRecords = data.records.filter(row => row.RBE === currentRBE && (currentTC === 'ALL' || row.TC_Display === currentTC));

            const makeTd = (text, cls) => {
                const td = document.createElement('td');
                if (cls) td.className = cls;
                td.textContent = text ?? '';
                return td;
            };
            filteredRecords.forEach((row, i) => {
                const tr = document.createElement('tr');
                tr.className = 'alarm-row';
                tr.appendChild(makeTd(i + 1, 'text-center'));
                // Checkbox — exclude this postcode from Route Map (persisted in localStorage)
                const pc = (row.Postcode || '').trim();
                const shouldCheck = !!pc && excludedPostcodes.has(pc);
                const radioTd = document.createElement('td');
                radioTd.className = 'text-center';
                const radio = document.createElement('input');
                radio.type = 'checkbox';
                radio.value = pc;
                radio.className = 'exclude-radio';
                radio.title = 'Check to exclude this postcode from Route Map';
                radio.checked = shouldCheck;
                radio.addEventListener('change', function() {
                    if (this.checked) {
                        excludedPostcodes.add(pc);
                    } else {
                        excludedPostcodes.delete(pc);
                    }
                    saveMask();
                    updateBadges();
                });
                radioTd.appendChild(radio);
                tr.appendChild(radioTd);
                tr.appendChild(makeTd(row.Postcode));
                tr.appendChild(makeTd(row.TC_Display));
                tr.appendChild(makeTd(row.Pfx));
                // Block — clickable link → /block_detail (new tab)
                const blockTd = document.createElement('td');
                const blockLink = document.createElement('a');
                blockLink.href = '/block_detail?tc=' + encodeURIComponent(row.TC_Display || '')
                               + '&pfx=' + encodeURIComponent(row.Pfx || '')
                               + '&block=' + encodeURIComponent(row.Block || '');
                blockLink.target = '_blank';
                blockLink.rel = 'noopener noreferrer';
                blockLink.style.cssText = 'text-decoration:none;color:inherit;border-bottom:1px dashed #aaa;cursor:pointer;';
                blockLink.textContent = row.Block ?? '';
                blockTd.appendChild(blockLink);
                tr.appendChild(blockTd);
                tr.appendChild(makeTd(row.Lift));
                const addrTd = document.createElement('td');
                addrTd.title = row.Address ?? '';
                const link = document.createElement('a');
                link.href = '#';
                link.className = 'addr-link';
                link.style.cssText = 'text-decoration:none;color:inherit;border-bottom:1px dashed #666;cursor:pointer;';
                link.textContent = row.Address ?? '';
                link.onclick = (e) => { e.preventDefault(); openOneMap(row.Block, row.Address, link); };
                addrTd.appendChild(link);
                tr.appendChild(addrTd);
                tr.appendChild(makeTd(row.LCOY));
                tr.appendChild(makeTd(fmtDate(row['Status Date'])));
                tr.appendChild(makeTd(row.RBE_Display));
                tbody.appendChild(tr);
            });
            updateBadges();
        }

        function sortByExclude(btn) {
            const currentDir = sortDirections['exclude'] || 'desc';
            const newDir = currentDir === 'asc' ? 'desc' : 'asc';
            sortDirections = { 'exclude': newDir };
            document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('asc', 'desc'));
            btn.classList.add(newDir);
            data.records.sort((a, b) => {
                const aEx = excludedPostcodes.has((a.Postcode || '').trim()) ? 1 : 0;
                const bEx = excludedPostcodes.has((b.Postcode || '').trim()) ? 1 : 0;
                return newDir === 'asc' ? bEx - aEx : aEx - bEx;
            });
            render();
        }

        function sortTable(colIndex, btn) {
            const currentDir = sortDirections[colIndex] || 'desc';
            const newDir = currentDir === 'asc' ? 'desc' : 'asc';
            sortDirections = { [colIndex]: newDir };
            
            document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('asc', 'desc'));
            btn.classList.add(newDir);

            data.records.sort((a, b) => {
                 let valA, valB;
                 // Map column index to data keys
                 const keys = ['_index', 'Postcode', 'TC_Display', 'Pfx', 'Block', 'Lift', 'Address', 'LCOY', 'Status Date', 'RBE_Display'];
                 const key = keys[colIndex];
                
                valA = a[key] || '';
                valB = b[key] || '';

                if (colIndex === 4) { // Block - Natural Sort
                    return newDir === 'asc' ? 
                        String(valA).localeCompare(String(valB), undefined, { numeric: true }) : 
                        String(valB).localeCompare(String(valA), undefined, { numeric: true });
                }
                if (colIndex === 0) { // # Index
                    return newDir === 'asc' ? parseFloat(valA) - parseFloat(valB) : parseFloat(valB) - parseFloat(valA);
                }
                if (colIndex === 8) { // Status Date
                    return newDir === 'asc' ? new Date(valA) - new Date(valB) : new Date(valB) - new Date(valA);
                }
                return newDir === 'asc' ? 
                    String(valA).localeCompare(String(valB)) : 
                    String(valB).localeCompare(String(valA));
            });
            render();
        }

        async function openOneMap(block, address, linkEl) {
            const searchVal = encodeURIComponent(`${block} ${address}`);
            const apiUrl = `/api/onemap/search?searchVal=${searchVal}&returnGeom=Y&getAddrDetails=Y&pageNum=1`;
            const origText = linkEl.textContent;
            linkEl.textContent = '⏳ ' + origText;
            linkEl.style.pointerEvents = 'none';
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), 8000);
            try {
                const resp = await fetch(apiUrl, { signal: controller.signal });
                clearTimeout(timer);
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const json = await resp.json();
                if (Array.isArray(json.results) && json.results.length > 0) {
                    const r = json.results[0];
                    const lat = parseFloat(r.LATITUDE);
                    const lng = parseFloat(r.LONGITUDE);
                    if (!isFinite(lat) || !isFinite(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180) {
                        throw new Error('Invalid coordinates');
                    }
                    const mapUrl = new URL('https://www.onemap.gov.sg/main/v2/');
                    mapUrl.searchParams.set('lat', lat.toFixed(6));
                    mapUrl.searchParams.set('lng', lng.toFixed(6));
                    mapUrl.searchParams.set('zoomLevel', '18');
                    mapUrl.searchParams.set('marker', `${lat.toFixed(6)},${lng.toFixed(6)},${block} ${address}`);
                    window.open(mapUrl.toString(), '_blank');
                } else {
                    window.open(`https://www.onemap.gov.sg/main/v2/?query=${searchVal}`, '_blank');
                }
            } catch(e) {
                clearTimeout(timer);
                window.open(`https://www.onemap.gov.sg/main/v2/?query=${searchVal}`, '_blank');
            } finally {
                linkEl.textContent = origText;
                linkEl.style.pointerEvents = '';
            }
        }

        function setRBE(rbe) {
            if (!['COMF', 'IOF'].includes(rbe)) return;
            currentRBE = rbe; currentTC = 'ALL';
            const themeColor = rbe === 'COMF' ? 'rgb(153, 87, 255)' : 'rgb(34, 213, 254)';
            document.documentElement.style.setProperty('--theme-color', themeColor);
            document.getElementById('comfBtn').classList.toggle('active', rbe === 'COMF');
            document.getElementById('iofBtn').classList.toggle('active', rbe === 'IOF');
            render();
        }
        function setTC(tc) {
            if (tc !== 'ALL' && !Object.keys(data.tc_stats[currentRBE] || {}).includes(tc)) return;
            currentTC = tc; render();
        }
        
        document.getElementById('comfBtn').onclick = () => setRBE('COMF');
        document.getElementById('iofBtn').onclick = () => setRBE('IOF');
        document.getElementById('routeBtn').onclick = openRouteMap;
        // Immediately show correct counts (including any saved mask state) before render()
        updateBadges();

        function buildMapHtml(records, comfCur, comfTot, iofCur, iofTot) {
            const rJson = JSON.stringify(records).replace(/&/g,'\\u0026').replace(/</g,'\\u003c').replace(/>/g,'\\u003e');
            return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<base href="${window.location.origin}/">
<title>ELTI Route Map</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.min.css">
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;display:flex;flex-direction:column;font-family:'Segoe UI',Tahoma,sans-serif;overflow:hidden}
#topbar{flex-shrink:0;background:rgba(255,255,255,.96);padding:8px 14px;display:flex;align-items:center;gap:10px;box-shadow:0 2px 6px rgba(0,0,0,.15);flex-wrap:wrap}
#topbar h2{font-size:15px;color:#333;margin:0;white-space:nowrap}
#status-badge{background:#555;color:#fff;border-radius:20px;padding:3px 10px;font-size:12px;white-space:nowrap}
#legend{display:flex;gap:12px;align-items:center}
.legend-item{display:flex;align-items:center;gap:5px;font-size:12px;color:#333}
.legend-dot{width:12px;height:12px;border-radius:50%;flex-shrink:0}
#map{flex:1;min-height:200px}
@media(max-width:600px){#topbar{padding:6px 8px;gap:7px}#topbar h2{font-size:13px}#legend{gap:8px;flex-wrap:wrap}.legend-item{font-size:11px}#status-badge{font-size:11px;padding:2px 8px}}
@media(max-width:400px){#topbar h2{font-size:12px}#legend{gap:5px}}
<\/style>
</head>
<body>
<div id="topbar">
  <h2>ELTI Route Map</h2>
  <span id="status-badge">Loading…</span>
  <div id="legend">
    <div class="legend-item"><span class="legend-dot" style="background:#9957ff"></span>COMF ${comfCur}/${comfTot}</div>
    <div class="legend-item"><span class="legend-dot" style="background:#22d5fe"></span>IOF ${iofCur}/${iofTot}</div>
    <div class="legend-item">Route ${comfCur+iofCur}/${comfTot+iofTot}</div>
  </div>
</div>
<div id="map"></div>
<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.min.js"><\/script>
<script>
(function(){
const records=${rJson};
const map=L.map("map").setView([1.3521,103.8198],12);
L.tileLayer("https://www.onemap.gov.sg/maps/tiles/Default/{z}/{x}/{y}.png",{maxZoom:19,attribution:'<img src="https://www.onemap.gov.sg/web-assets/images/logo/om_logo.png" style="height:20px;vertical-align:middle"> OneMap &copy; contributors, Singapore Land Authority'}).addTo(map);
const COMF_C="#9957ff",IOF_C="#22d5fe";
const pcMap={};
records.forEach(r=>{
  const pc=(r.Postcode||"").trim();
  if(!pc||pc==="-")return;
  if(!pcMap[pc])pcMap[pc]={comf:[],iof:[]};
  (r.RBE==="COMF"?pcMap[pc].comf:pcMap[pc].iof).push(r);
});
const pcs=Object.keys(pcMap);
const st=document.getElementById("status-badge");
let ok=0,fail=0;
function mkPop(pc,comf,iof,addr){
  let h='<div style="font-size:13px;max-width:260px"><b>Postcode '+pc+'</b>';
  if(addr)h+='<br><small style="color:#666">'+addr+'</small>';
  function rows(list,color,label){
    if(!list.length)return;
    h+='<div style="margin-top:5px;border-top:1px solid #eee;padding-top:4px"><span style="color:'+color+';font-weight:bold">'+label+' ('+list.length+')</span>';
    list.forEach(r=>{h+='<br><small>Blk '+(r.Block||'-')+' · '+(r.Lift||'-')+' · '+(r.TC_Display||'-')+'</small>';});
    h+='</div>';
  }
  rows(comf,COMF_C,"COMF");rows(iof,IOF_C,"IOF");
  return h+'</div>';
}
async function fetchOm(pc){
  const ctrl=new AbortController();
  const tid=setTimeout(()=>ctrl.abort(),15000);
  try{
    const r=await fetch(
      '/api/onemap/search?searchVal='+encodeURIComponent(pc)+'&returnGeom=Y&getAddrDetails=Y&pageNum=1',
      {signal:ctrl.signal}
    );
    clearTimeout(tid);
    if(!r.ok)return null;
    return await r.json();
  }catch(e){clearTimeout(tid);return null;}
}
async function fp(pc){
  try{
    const j=await fetchOm(pc);
    if(j&&Array.isArray(j.results)&&j.results.length){
      const r0=j.results[0];
      const lat=parseFloat(r0.LATITUDE),lng=parseFloat(r0.LONGITUDE);
      if(isFinite(lat)&&isFinite(lng)){
        const {comf,iof}=pcMap[pc];
        const pop=mkPop(pc,comf,iof,r0.ADDRESS||"");
        const both=comf.length>0&&iof.length>0;
        if(comf.length)L.circleMarker(both?[lat,lng-0.00004]:[lat,lng],{radius:8,fillColor:COMF_C,color:"#fff",weight:1.5,opacity:1,fillOpacity:.85}).addTo(map).bindPopup(pop);
        if(iof.length)L.circleMarker(both?[lat,lng+0.00004]:[lat,lng],{radius:8,fillColor:IOF_C,color:"#fff",weight:1.5,opacity:1,fillOpacity:.85}).addTo(map).bindPopup(pop);
        ok++;
      }else{fail++;}
    }else{fail++;}
  }catch(e){fail++;}
  const done=ok+fail;
  if(done<pcs.length)st.textContent="Fetching "+done+"/"+pcs.length+"…";
  else{st.style.background=fail>0?"#e67e22":"#27ae60";st.textContent=ok+" marker"+(ok!==1?"s":"")+" loaded"+(fail>0?", "+fail+" failed":"");}
}
async function go(){for(let i=0;i<pcs.length;i+=5)await Promise.all(pcs.slice(i,i+5).map(fp));}
if(!pcs.length)st.textContent="No postcodes found";
else go();
})();
<\/script>
</body>
</html>`;
        }
        function openRouteMap() {
            let comfEx = 0, iofEx = 0;
            data.records.forEach(r => {
                const pc = (r.Postcode || '').trim();
                if (!pc || pc === '-' || !excludedPostcodes.has(pc)) return;
                if (r.RBE === 'COMF') comfEx++;
                else if (r.RBE === 'IOF') iofEx++;
            });
            const comfCur = data.comf_count - comfEx;
            const iofCur = data.iof_count - iofEx;
            const allRec = data.records.filter(r => {
                const pc = (r.Postcode || '').trim();
                if (!pc || pc === '-') return false;
                if (excludedPostcodes.size > 0 && excludedPostcodes.has(pc)) return false;
                return true;
            });
            const blob = new Blob([buildMapHtml(allRec, comfCur, data.comf_count, iofCur, data.iof_count)], {type: 'text/html'});
            const url = URL.createObjectURL(blob);
            window.open(url, '_blank');
            setTimeout(() => URL.revokeObjectURL(url), 60000);
        }
        render();
    </script>
</body>
</html>
"""

# ── D1 helpers ────────────────────────────────────────────────────────────────

def _dv(row, key, default=""):
    """Safe getter for D1 result rows (supports both dict and attribute access)."""
    try:
        v = row[key]
    except (KeyError, TypeError):
        try:
            v = getattr(row, key, None)
        except Exception:
            return default
    return str(v) if v is not None else default


_EMPTY_PAYLOAD = {"records": [], "comf_count": 0, "iof_count": 0,
                  "tc_stats": {"COMF": {}, "IOF": {}}, "last_updated": "Never"}


async def _d1_load(env):
    """Read all alarm records from D1 (LEFT JOIN with Lift Talk masterlist).
    Returns None if D1 has no data (caller should fall back to KV)."""
    res = await env.elti_db.prepare(
        "SELECT r.tc, r.pfx, r.block, r.lift, r.address, "
        "  COALESCE(NULLIF(TRIM(m.postal_code),''), r.postcode) AS postcode, "
        "  r.lcoy, r.status_date, r.rbe, r.rbe_display, r.status, "
        "  m.town_council, m.full_add, m.lift_names_all, m.interface, m.lss "
        "FROM records r "
        "LEFT JOIN masterlist_lt m ON m.id = ( "
        "  SELECT id FROM masterlist_lt "
        "  WHERE (tc = r.tc AND pfx = r.pfx AND block = r.block) "
        "     OR (postal_code != '' AND r.postcode != '' AND postal_code = r.postcode) "
        "  ORDER BY CASE WHEN tc = r.tc AND pfx = r.pfx AND block = r.block THEN 0 ELSE 1 END "
        "  LIMIT 1 "
        ") "
        "ORDER BY r.rbe, r.tc, r.pfx, r.block"
    ).all()
    rows = res.results if res.results else []
    if not rows:
        return None

    records = []
    for row in rows:
        records.append({
            "Postcode":      _dv(row, "postcode"),
            "TC_Display":    _dv(row, "tc") or "-",
            "Pfx":           _dv(row, "pfx"),
            "Block":         _dv(row, "block"),
            "Lift":          _dv(row, "lift"),
            "Address":       _dv(row, "address"),
            "LCOY":          _dv(row, "lcoy"),
            "Status Date":   _dv(row, "status_date") or "-",
            "RBE":           _dv(row, "rbe"),
            "RBE_Display":   _dv(row, "rbe_display") or _dv(row, "rbe"),
            "Status":        int(_dv(row, "status") or 1),
            # Lift Talk enrichment fields (empty string when no LT match)
            "Town_Council":  _dv(row, "town_council"),
            "Full_Add":      _dv(row, "full_add"),
            "Lift_Names_All":_dv(row, "lift_names_all"),
            "Interface":     _dv(row, "interface"),
            "LSS":           _dv(row, "lss"),
        })

    comf = [r for r in records if r["RBE"] == "COMF"]
    iof  = [r for r in records if r["RBE"] == "IOF"]
    tc_stats: dict = {"COMF": {}, "IOF": {}}
    for r in comf:
        tc_stats["COMF"][r["TC_Display"]] = tc_stats["COMF"].get(r["TC_Display"], 0) + 1
    for r in iof:
        tc_stats["IOF"][r["TC_Display"]]  = tc_stats["IOF"].get(r["TC_Display"],  0) + 1

    meta = await env.elti_db.prepare(
        "SELECT value FROM meta WHERE key = 'last_updated'"
    ).first()
    last_updated = _dv(meta, "value") if meta else "Never"

    return {"records": records, "comf_count": len(comf), "iof_count": len(iof),
            "tc_stats": tc_stats, "last_updated": last_updated or "Never"}


async def _d1_write(env, data):
    """Persist a sync payload to D1 (delete-then-insert, batched ≤100 stmts)."""
    records = data.get("records", [])
    last_updated = data.get("last_updated", "")

    # Clear previous alarm snapshot
    await env.elti_db.prepare("DELETE FROM records").run()

    # Prepare INSERT statements
    sql = (
        "INSERT INTO records "
        "(tc, pfx, block, lift, address, postcode, lcoy, "
        " status_date, rbe, rbe_display, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    stmts = [
        env.elti_db.prepare(sql).bind(
            r.get("TC_Display", ""), r.get("Pfx", ""),
            r.get("Block", ""),     r.get("Lift", ""),
            r.get("Address", ""),   r.get("Postcode", ""),
            r.get("LCOY", ""),      r.get("Status Date", ""),
            r.get("RBE", ""),       r.get("RBE_Display", ""),
            int(r.get("Status", 1) or 1),
        )
        for r in records
    ]
    for i in range(0, len(stmts), 100):
        await env.elti_db.batch(stmts[i:i + 100])

    await env.elti_db.prepare(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('last_updated', ?)"
    ).bind(last_updated).run()
    print(f"[d1] wrote {len(records)} records, last_updated={last_updated}")


# ── Query-string parser ────────────────────────────────────────────────────────

def _parse_qs(url: str) -> dict:
    """Decode query parameters from a full URL string."""
    qs = url.split("?", 1)[1] if "?" in url else ""
    params: dict = {}
    for part in qs.split("&"):
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        v = v.replace("+", " ")
        # Decode %XX sequences
        segs = v.split("%")
        decoded = [segs[0]]
        for seg in segs[1:]:
            if len(seg) >= 2:
                try:
                    decoded.append(chr(int(seg[:2], 16)))
                    decoded.append(seg[2:])
                    continue
                except ValueError:
                    pass
            decoded.append("%" + seg)
        params[k] = "".join(decoded)
    return params


# ── Block-detail D1 loader ─────────────────────────────────────────────────────

async def _d1_load_block(env, tc: str, pfx: str, block: str) -> list:
    """Return row dicts for one block (both RBEs) with LT enrichment.
    Uses the same postcode-fallback JOIN as _d1_load().
    """
    res = await env.elti_db.prepare(
        "SELECT r.tc, r.pfx, r.block, r.lift, r.address, "
        "  COALESCE(NULLIF(TRIM(m.postal_code),''), r.postcode) AS postcode, "
        "  r.lcoy, r.status_date, r.rbe, r.rbe_display, r.status, "
        "  m.town_council, m.full_add, m.postal_code AS lt_postal_code, "
        "  m.lift_names_all, m.interface, m.lss "
        "FROM records r "
        "LEFT JOIN masterlist_lt m ON m.id = ( "
        "  SELECT id FROM masterlist_lt "
        "  WHERE (tc = r.tc AND pfx = r.pfx AND block = r.block) "
        "     OR (postal_code != '' AND r.postcode != '' AND postal_code = r.postcode) "
        "  ORDER BY CASE WHEN tc = r.tc AND pfx = r.pfx AND block = r.block THEN 0 ELSE 1 END "
        "  LIMIT 1 "
        ") "
        "WHERE r.tc = ? AND r.pfx = ? AND r.block = ? "
        "ORDER BY r.rbe"
    ).bind(tc, pfx, block).all()
    rows = res.results if res.results else []
    result = []
    for row in rows:
        result.append({
            "tc":             _dv(row, "tc"),
            "pfx":            _dv(row, "pfx"),
            "block":          _dv(row, "block"),
            "lift":           _dv(row, "lift"),
            "address":        _dv(row, "address"),
            "postcode":       _dv(row, "postcode"),
            "lcoy":           _dv(row, "lcoy"),
            "status_date":    _dv(row, "status_date"),
            "rbe":            _dv(row, "rbe"),
            "rbe_display":    _dv(row, "rbe_display"),
            "status":         _dv(row, "status") or "1",
            "town_council":   _dv(row, "town_council"),
            "full_add":       _dv(row, "full_add"),
            "lt_postal_code": _dv(row, "lt_postal_code"),
            "lift_names_all": _dv(row, "lift_names_all"),
            "interface":      _dv(row, "interface"),
            "lss":            _dv(row, "lss"),
        })
    return result


# ── GitHub workflow trigger ────────────────────────────────────────────────────

async def _trigger_github_workflow(env):
    token = env.GITHUB_TOKEN if hasattr(env, "GITHUB_TOKEN") else None
    if not token:
        print("[cron] GITHUB_TOKEN not set, skipping dispatch")
        return

    init = Object.new()
    init.method = "POST"
    init.body = json.dumps({"ref": "main"})
    init.headers = Headers.new([
        ["Authorization", f"Bearer {token}"],
        ["Accept", "application/vnd.github+json"],
        ["X-GitHub-Api-Version", "2022-11-28"],
        ["Content-Type", "application/json"],
        ["User-Agent", "ELTI-CF-Worker/1.0"],
    ])

    resp = await fetch(
        "https://api.github.com/repos/la72b27/elti/actions/workflows/sync_tms.yml/dispatches",
        init,
    )
    print(f"[cron] GitHub dispatch → {resp.status}")  # 204 = success


async def on_scheduled(controller, env, ctx):
    await _trigger_github_workflow(env)


# ── Request handler ────────────────────────────────────────────────────────────

async def on_fetch(request, env):
    try:
        url    = request.url
        method = request.method

        # ── GET /block_detail ────────────────────────────────────────────────
        if method == "GET" and "/block_detail" in url:
            params  = _parse_qs(url)
            tc_p    = params.get("tc",    "").strip()
            pfx_p   = params.get("pfx",  "").strip()
            block_p = params.get("block", "").strip()
            if not tc_p or not block_p:
                return Response.new(
                    "Missing tc or block parameter", status=400,
                    headers=Headers.new([["Content-Type", "text/plain; charset=utf-8"]]))
            rows = []
            try:
                rows = await _d1_load_block(env, tc_p, pfx_p, block_p)
            except Exception as e:
                print(f"[block_detail error] {e}")
            html = block_detail.render_html(rows, tc_p, pfx_p, block_p)
            return Response.new(html, headers=Headers.new([
                ["Content-Type",           "text/html; charset=utf-8"],
                ["X-Content-Type-Options", "nosniff"],
                ["X-Frame-Options",        "DENY"],
                ["Referrer-Policy",        "strict-origin-when-cross-origin"],
            ]))

        # ── GET /api/token ──────────────────────────────────────────────────
        if method == "GET" and "/api/token" in url:
            auth_token     = request.headers.get("X-Update-Token")
            expected_token = env.UPDATE_TOKEN if hasattr(env, "UPDATE_TOKEN") else None
            if expected_token and auth_token != expected_token:
                return Response.new(json.dumps({"error": "Unauthorized"}), status=401,
                                    headers=Headers.new([["Content-Type", "application/json"]]))
            force = "refresh=1" in url
            tok = await onemap.get_token(env, force=force)
            return Response.new(json.dumps({"token": tok}),
                                headers=Headers.new([["Content-Type", "application/json"]]))

        # ── GET /api/onemap/search ──────────────────────────────────────────
        if method == "GET" and "/api/onemap/search" in url:
            qs     = url.split("?", 1)[1] if "?" in url else ""
            result = await onemap.search(env, qs)
            return Response.new(json.dumps(result),
                                headers=Headers.new([["Content-Type", "application/json"]]))

        # ── POST /trigger ───────────────────────────────────────────────────
        if method == "POST" and "/trigger" in url:
            auth_token     = request.headers.get("X-Update-Token")
            expected_token = env.UPDATE_TOKEN if hasattr(env, "UPDATE_TOKEN") else None
            if expected_token and auth_token != expected_token:
                return Response.new(json.dumps({"error": "Unauthorized"}), status=401,
                                    headers=Headers.new([["Content-Type", "application/json"]]))
            await _trigger_github_workflow(env)
            return Response.new(json.dumps({"triggered": True}),
                                headers=Headers.new([["Content-Type", "application/json"]]))

        # ── POST /api/mask ──────────────────────────────────────────────────
        if method == "POST" and "/api/mask" in url:
            payload_str = await request.text()
            mask_data   = json.loads(payload_str)
            if not isinstance(mask_data, list):
                return Response.new(json.dumps({"error": "Invalid format"}), status=400,
                                    headers=Headers.new([["Content-Type", "application/json"]]))
            clean = [str(p).strip()[:10] for p in mask_data
                     if isinstance(p, (str, int)) and str(p).strip()][:2000]
            await env.ELTI_DATA.put("mask_data", json.dumps(clean))
            return Response.new(json.dumps({"saved": len(clean)}),
                                headers=Headers.new([["Content-Type", "application/json"]]))

        # ── POST /api/lt/upload  (Lift Talk masterlist enrichment) ────────────
        if method == "POST" and "/api/lt/upload" in url:
            auth_token     = request.headers.get("X-Update-Token")
            expected_token = env.UPDATE_TOKEN if hasattr(env, "UPDATE_TOKEN") else None
            if expected_token and auth_token != expected_token:
                return Response.new(json.dumps({"error": "Unauthorized"}), status=401,
                                    headers=Headers.new([["Content-Type", "application/json"]]))

            payload_str = await request.text()
            data        = json.loads(payload_str)
            lt_records  = data.get("records", [])

            sql = (
                "INSERT OR REPLACE INTO masterlist_lt "
                "(tc, pfx, block, town_council, full_add, postal_code, "
                " lift_names_all, interface, lss) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            )
            stmts = [
                env.elti_db.prepare(sql).bind(
                    r.get("tc", ""),           r.get("pfx", ""),
                    r.get("block", ""),        r.get("town_council", ""),
                    r.get("full_add", ""),     r.get("postal_code", ""),
                    r.get("lift_names_all", ""),r.get("interface", ""),
                    r.get("lss", ""),
                )
                for r in lt_records
                if r.get("tc") and r.get("block") is not None
            ]
            for i in range(0, len(stmts), 100):
                await env.elti_db.batch(stmts[i:i + 100])

            print(f"[lt] upserted {len(stmts)} masterlist_lt rows")
            return Response.new(json.dumps({"upserted": len(stmts)}),
                                headers=Headers.new([["Content-Type", "application/json"]]))

        # ── POST /update  (sync script pushes here) ─────────────────────────
        if method == "POST" and "/update" in url:
            auth_token     = request.headers.get("X-Update-Token")
            expected_token = env.UPDATE_TOKEN if hasattr(env, "UPDATE_TOKEN") else None
            if expected_token and auth_token != expected_token:
                return Response.new(json.dumps({"error": "Unauthorized"}), status=401,
                                    headers=Headers.new([["Content-Type", "application/json"]]))

            payload_str = await request.text()
            data        = json.loads(payload_str)

            # Write to D1 (primary store)
            try:
                await _d1_write(env, data)
            except Exception as e:
                print(f"[d1 write error] {e}")

            # Keep KV as fallback cache
            await env.ELTI_DATA.put("cached_data", payload_str)

            n = len(data.get("records", []))
            return Response.new(json.dumps({"success": True, "records": n}),
                                headers=Headers.new([["Content-Type", "application/json"]]))

        # ── GET / (main dashboard) ──────────────────────────────────────────
        # 1. Try D1 (primary)
        data_dict = None
        try:
            data_dict = await _d1_load(env)
        except Exception as e:
            print(f"[d1 load error] {e}")

        # 2. Fall back to KV if D1 is empty or errored
        if data_dict is None:
            stored    = await env.ELTI_DATA.get("cached_data")
            data_json = stored if stored else json.dumps(_EMPTY_PAYLOAD)
        else:
            data_json = json.dumps(data_dict)

        # Mask list (stored in KV)
        mask_stored = await env.ELTI_DATA.get("mask_data")
        mask_list   = json.loads(mask_stored) if mask_stored else []

        # Escape < > & to prevent </script> injection
        def _safe(s):
            return s.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")

        html = HTML_TEMPLATE.replace("{{DATA_JSON}}",   _safe(data_json))
        html = html.replace("{{MASK_JSON}}",            _safe(json.dumps(mask_list)))
        html = html.replace("{{LOGO_BASE64}}",          LOGO_BASE64)

        return Response.new(html, headers=Headers.new([
            ["Content-Type",             "text/html; charset=utf-8"],
            ["X-Content-Type-Options",   "nosniff"],
            ["X-Frame-Options",          "DENY"],
            ["Referrer-Policy",          "strict-origin-when-cross-origin"],
            ["Content-Security-Policy",
             "default-src 'self'; "
             "script-src 'unsafe-inline' https://cdn.jsdelivr.net; "
             "style-src 'unsafe-inline' https://cdn.jsdelivr.net; "
             "connect-src 'self' https://www.onemap.gov.sg https://cdn.jsdelivr.net; "
             "img-src 'self' data: https://*.tile.openstreetmap.org https://www.onemap.gov.sg; "
             "frame-ancestors 'none'"],
        ]))

    except Exception as e:
        print(f"[error] {e}")
        return Response.new(json.dumps({"error": "Internal server error"}), status=500,
                            headers=Headers.new([["Content-Type", "application/json"]]))

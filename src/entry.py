from js import Response, Headers, fetch, Object
import json

VERSION = "1.3.5.5"

# Base64 encoded logo
LOGO_BASE64 = "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"

# 完整的 HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'unsafe-inline' https://cdn.jsdelivr.net; connect-src 'self' https://www.onemap.gov.sg; img-src 'self' data: https://*.tile.openstreetmap.org; frame-ancestors 'none'">
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
        @media (max-width: 768px) {
            body { padding: 10px; }
            .container-fluid { padding: 12px; }
            .logo-img { height: 72px; }
        }
        .btn-route-toggle { border-color: rgb(175, 245, 45); color: rgb(60, 100, 0); }
        .btn-route-toggle:hover { background-color: rgb(175, 245, 45); color: #222; border-color: rgb(175, 245, 45); }
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
            <button class="btn btn-stat btn-comf-toggle active" id="comfBtn">COMF 0</button>
            <button class="btn btn-stat btn-iof-toggle" id="iofBtn">IOF 0</button>
            <button class="btn btn-stat btn-route-toggle" id="routeBtn">Route</button>
        </div>

        <div class="tc-stats" id="tcContainer"></div>
        <div class="table-container">
            <table class="table table-hover table-bordered">
                <thead>
                    <tr>
                        <th><button class="sort-btn" onclick="sortTable(0, this)">#</button></th>
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

        function render() {
            document.getElementById('comfBtn').textContent = `COMF ${data.comf_count}`;
            document.getElementById('iofBtn').textContent = `IOF ${data.iof_count}`;
            
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
            let visibleCount = 0;
            
            // Filter records first
            let filteredRecords = data.records.filter(row => row.RBE === currentRBE && (currentTC === 'ALL' || row.TC_Display === currentTC));
            
            const makeTd = (text, cls) => {
                const td = document.createElement('td');
                if (cls) td.className = cls;
                td.textContent = text ?? '';
                return td;
            };
            filteredRecords.forEach(row => {
                visibleCount++;
                const tr = document.createElement('tr');
                tr.className = 'alarm-row';
                tr.appendChild(makeTd(visibleCount, 'text-center row-index'));
                tr.appendChild(makeTd(row.Postcode));
                tr.appendChild(makeTd(row.TC_Display));
                tr.appendChild(makeTd(row.Pfx));
                tr.appendChild(makeTd(row.Block));
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
            const apiUrl = `https://www.onemap.gov.sg/api/common/elastic/search?searchVal=${searchVal}&returnGeom=Y&getAddrDetails=Y&pageNum=1`;
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

        function buildMapHtml(records) {
            const rJson = JSON.stringify(records).replace(/&/g,'\\u0026').replace(/</g,'\\u003c').replace(/>/g,'\\u003e');
            return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
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
@media(max-width:480px){#topbar{padding:6px 10px}#topbar h2{font-size:13px}}
<\/style>
</head>
<body>
<div id="topbar">
  <h2>ELTI Route Map</h2>
  <span id="status-badge">Loading…</span>
  <div id="legend">
    <div class="legend-item"><span class="legend-dot" style="background:#9957ff"></span>COMF</div>
    <div class="legend-item"><span class="legend-dot" style="background:#22d5fe"></span>IOF</div>
  </div>
</div>
<div id="map"></div>
<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.min.js"><\/script>
<script>
(function(){
const records=${rJson};
const ONEMAP_EMAIL='qi.liu@softgridinc.com';
const ONEMAP_PWD='S@ftgr1dSensing';
let token='';
const map=L.map("map").setView([1.3521,103.8198],12);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
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
async function getToken(){
  const ctrl=new AbortController();
  const tid=setTimeout(()=>ctrl.abort(),8000);
  try{
    const r=await fetch('https://www.onemap.gov.sg/api/auth/post/getToken',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({email:ONEMAP_EMAIL,password:ONEMAP_PWD}),
      signal:ctrl.signal
    });
    clearTimeout(tid);
    if(r.ok){const j=await r.json();if(j.access_token)return j.access_token;}
  }catch(e){clearTimeout(tid);}
  return token;
}
async function fetchOm(pc,tok){
  const ctrl=new AbortController();
  const tid=setTimeout(()=>ctrl.abort(),10000);
  try{
    return await fetch(
      "https://www.onemap.gov.sg/api/common/elastic/search?searchVal="+encodeURIComponent(pc)+"&returnGeom=Y&getAddrDetails=Y&pageNum=1",
      {headers:{Authorization:'Bearer '+tok},signal:ctrl.signal}
    );
  }finally{clearTimeout(tid);}
}
async function fp(pc){
  try{
    let res=await fetchOm(pc,token);
    if(res.status===401){token=await getToken();res=await fetchOm(pc,token);}
    if(res.ok){
      const j=await res.json();
      if(Array.isArray(j.results)&&j.results.length){
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
    }else{fail++;}
  }catch(e){fail++;}
  const done=ok+fail;
  if(done<pcs.length)st.textContent="Fetching "+done+"/"+pcs.length+"…";
  else{st.style.background=fail>0?"#e67e22":"#27ae60";st.textContent=ok+" marker"+(ok!==1?"s":"")+" loaded"+(fail>0?", "+fail+" failed":"");}
}
async function go(){
  token=await getToken();
  for(let i=0;i<pcs.length;i+=5)await Promise.all(pcs.slice(i,i+5).map(fp));
}
if(!pcs.length)st.textContent="No postcodes found";
else go();
})();
<\/script>
</body>
</html>`;
        }
        function openRouteMap() {
            const allRec = data.records.filter(r => r.Postcode && r.Postcode.trim() !== '' && r.Postcode.trim() !== '-');
            const blob = new Blob([buildMapHtml(allRec)], {type: 'text/html'});
            const url = URL.createObjectURL(blob);
            window.open(url, '_blank');
            setTimeout(() => URL.revokeObjectURL(url), 60000);
        }
        render();
    </script>
</body>
</html>
"""

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


async def on_fetch(request, env):
    try:
        url = request.url
        method = request.method
        
        if method == "POST" and "/trigger" in url:
            auth_token = request.headers.get("X-Update-Token")
            expected_token = env.UPDATE_TOKEN if hasattr(env, "UPDATE_TOKEN") else None
            if expected_token and auth_token != expected_token:
                return Response.new(json.dumps({"error": "Unauthorized"}), status=401, headers=Headers.new([["Content-Type", "application/json"]]))
            await _trigger_github_workflow(env)
            return Response.new(json.dumps({"triggered": True}), headers=Headers.new([["Content-Type", "application/json"]]))

        if method == "POST" and "/update" in url:
            # 安全校验：检查 Header 中的 Token 是否匹配
            auth_token = request.headers.get("X-Update-Token")
            expected_token = env.UPDATE_TOKEN if hasattr(env, "UPDATE_TOKEN") else None
            
            if expected_token and auth_token != expected_token:
                return Response.new(json.dumps({"error": "Unauthorized"}), status=401, headers=Headers.new([["Content-Type", "application/json"]]))

            payload_str = await request.text()
            json.loads(payload_str)
            await env.ELTI_DATA.put("cached_data", payload_str)
            return Response.new(json.dumps({"success": True}), headers=Headers.new([["Content-Type", "application/json"]]))

        stored = await env.ELTI_DATA.get("cached_data")
        data_json = stored if stored else json.dumps({"records":[], "comf_count":0, "iof_count":0, "tc_stats":{"COMF":{}, "IOF":{}}, "last_updated":"Never"})

        # 防止 data_json 中含有 </script> 等字符截断 <script> 块（服务端脚本注入）
        # 将 <、>、& 替换为 JSON 合法的 unicode 转义序列，JS JSON.parse 可正确还原
        safe_json = data_json.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")

        html = HTML_TEMPLATE.replace("{{DATA_JSON}}", safe_json)
        html = html.replace("{{LOGO_BASE64}}", LOGO_BASE64)
        
        return Response.new(html, headers=Headers.new([
            ["Content-Type", "text/html; charset=utf-8"],
            ["X-Content-Type-Options", "nosniff"],
            ["X-Frame-Options", "DENY"],
            ["Referrer-Policy", "strict-origin-when-cross-origin"],
            ["Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'unsafe-inline' https://cdn.jsdelivr.net; connect-src 'self' https://www.onemap.gov.sg; img-src 'self' data: https://*.tile.openstreetmap.org; frame-ancestors 'none'"],
        ]))
        
    except Exception as e:
        return Response.new(json.dumps({"error": str(e)}), status=500, headers=Headers.new([["Content-Type", "application/json"]]))

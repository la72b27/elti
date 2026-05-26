# ELTI – Changelog

## v1.3.7.7 – LMD Device ID + postcode-based block detail + LSS full coverage

### Changes made

**`migrations/0004_add_lmd_device_id.sql`** *(new)*

- `ALTER TABLE masterlist_lt ADD COLUMN lmd_device_id TEXT` — adds the LMD Device ID field sourced from Lift Talk - MasterList column 18.

**`scripts/upload_lt.py`**

- Added `"LMD Device ID": 18` to `_WANT` column mapping.
- `lmd_device_id` now included in every record uploaded to `/api/lt/upload`.

**`src/entry.py`**

- **`POST /api/lt/upload`**: INSERT OR REPLACE now writes `lmd_device_id` (10th bind param).
- **`GET /block_detail`**: Accepts `?postcode=<6-digit>` as an alternative to `?tc=&pfx=&block=`. When only `postcode` is supplied, the handler queries `masterlist_lt` for the matching `(tc, pfx, block)` tuple and proceeds with normal enrichment loading. Allows direct access to block detail for postcodes not currently in TMS alarms.
- **`_d1_load_block()`**:
  - LT query now selects `lmd_device_id` (and `lt_tc`, `lt_pfx`, `lt_block` for stub row assembly).
  - LSS postcode resolved from TMS postcode → LT postal_code → caller-supplied postcode (in priority order), removing the prior dependency on TMS rows being non-empty.
  - **Stub row (new)**: When no TMS alarm records exist but a `masterlist_lt` entry is found, returns a single synthetic row (`rbe=''`) populated with full LT + LSS enrichment data. This lets the block detail page render the Lift Talk Enrichment card for postcodes with no active alarms.
  - KV fallback now includes `lmd_device_id: ""` in the fallback row dict.
  - Accepts optional `postcode` argument used as fallback for LT/LSS lookups.

**`src/block_detail.py`**

- **Header card**: Right side now shows `lmd_device_id` (LT MasterList device serial) instead of `lmd_ip` (LSS IP address). Previous header displayed the LMD IP address; now shows the correct LMD Device ID string (e.g. `SFT2231001268`).
- **TMS Alarm card**: Rows with `rbe=''` (stub rows) are skipped; card correctly shows "No TMS alarm record found" when the block has no active alarms.
- **Lift Talk Enrichment left column**: Added `LMD Device ID` field below `Interface`.
- LT data detection now also triggers on `lmd_device_id` key.

**D1 data (direct update)**

- `lmd_device_id` backfilled for 7 postcodes: 670510, 651194, 680678, 760846, 210042, 640702, 730551.
- All 7 postcodes already had permanent entries in `masterlist_lt` and `masterlist_lss`; no new rows needed. Block detail is now accessible via `/block_detail?postcode=<pc>` for all 7, even for the 6 without active TMS alarms.

**`scripts/upload_lss.py`** *(updated)*

- **Root cause fix**: previous version only processed `EP1WM` hardware version rows. Many blocks use `EP1WB`, `EP2M`, `5300M`, `4409`, etc. as their network master — these were silently skipped, leaving their IP fields blank.
- New logic: processes **all hardware versions**. For each `postal_code`, the primary row is the first row (sorted by Lift) whose `IP Address` starts with `10.5.` — regardless of hardware version. Non-10.5 IPs are ignored for `lmd_ip` / `proxy_ip` / `vp_tun_ip` / `lmd_tun_ip`.
- DVR IP aggregation unchanged — still spans all lifts in the group.
- Result: `masterlist_lss` expanded from **2011 → 5490 records**; `proxy_ip` coverage from 1392 → 4658; `dvr_ip` from 1295 → 4211.

---

## v1.3.7.6 – LSS MasterList IP enrichment + block detail UI updates

### Changes made

**`migrations/0003_masterlist_lss.sql`** *(new)*

- New table `masterlist_lss` (unique per `postal_code`): stores LSS MasterList network fields — `lmd_ip`, `proxy_ip`, `vp_tun_ip`, `lmd_tun_ip`, `dvr_ip`.

**`scripts/upload_lss.py`** *(new)*

- One-time enrichment script. Reads `LSS - MasterList.xlsx`, filters to EP1WM rows, groups by `postal_code`, and POSTs to `/api/lss/upload`.
- Per block: primary LMD IP = `IP Address` (Lift A / first EP1WM row); Proxy IP = `Host2`; VP Tun IP = `Gateway1`; LMD Tun IP = VP Tun IP + 1 (computed); DVR IP = aggregated `dvrIP convert` per lift in format `A=x.x.x.x, B=x.x.x.x`.
- Data loaded directly via `wrangler d1 execute` (2011 records).

**`src/entry.py`**

- **`POST /api/lss/upload`**: New auth-guarded endpoint. Accepts `{"records": [...]}` and upserts into `masterlist_lss` (batch INSERT OR REPLACE, 100 per D1 batch).
- **`_d1_load_block()`**: Added Step 2b — queries `masterlist_lss` by TMS `postcode`; merges `lmd_ip`, `proxy_ip`, `vp_tun_ip`, `lmd_tun_ip`, `dvr_ip` into each row dict.

**`src/block_detail.py`**

- **Header card**: Block ID row now shows `lmd_ip` right-aligned as a monospace device identifier (no label text).
- **TMS Alarm card**: Merged into a single card; each RBE shown as one compact row `[COMF/IOF badge] [time value]` — no "Status Date" label, no separate card per RBE.
- **Lift Talk Enrichment right column**: Added LMD IP, Proxy IP, VP Tun IP, LMD Tun IP, DVR IP fields below existing LSS field.

---

## v1.3.7.5 – Block detail UX overhaul + Status Date timezone fix

### Changes made

**`src/entry.py`**

- **Postcode column → block_detail link**: Each postcode value in the main alarm table is now a clickable link to `/block_detail` (new tab). The Block column reverts to plain text.
- **`GET /block_detail` handler**: Also queries `meta.last_updated` from D1 and passes it to `block_detail.render_html()`.

**`src/block_detail.py`**

- **TMS Alarm card simplified**: Only the RBE badge (COMF / IOF) in the card header and a single "Status Date" field in the body — TC, Pfx, Block, Lift, LCOY, Postcode, and Status badge removed.
- **Lift Talk Enrichment card — two-column layout**: Town Council, Full Address, Lift Names, and Interface are stacked in the left column (`col-8`); LSS sits alone in the right column (`col-4`). A vertical divider separates the columns on desktop; on mobile they stack vertically.
- **Nav bar — show Updated time**: Removed the version badge; now shows `Updated: <last_updated>` from `meta` so users know when the data was last synced.
- **Address link — JS-powered OneMap lookup**: Changed from a static `?query=` URL to the same `openOneMap()` JS function used by the main dashboard. Calls `/api/onemap/search` to get precise lat/lng, falls back to `?query=` if the API fails. CSP updated to allow `script-src 'unsafe-inline'` and `connect-src 'self'`.

**`scripts/tms_transform.py`**

- **`_parse_date()` — timezone fix**: When the TMS API returns `setDate` as an ISO string without an explicit timezone (e.g. `"2026-05-14T09:03:00"`), Python's `datetime.fromisoformat` was treating it as local time (UTC on GitHub Actions) and then `astimezone(SGT)` added 8 hours, causing Status Date to appear 8 hours ahead of TMS website. Now: only performs the UTC→SGT conversion when the raw string contains `Z` or `+00:00`; otherwise formats the naive datetime directly (assumed already SGT). Affects the next TMS sync.

---

## v1.3.7.4 – Block detail fix: replace correlated subquery with two-query approach

### Bug fix

**`src/entry.py`**

- **`_d1_load_block()` — correlated subquery removed**: The previous `LEFT JOIN masterlist_lt m ON m.id = (SELECT id FROM masterlist_lt WHERE tc = r.tc ...)` failed at runtime with `no such column: r.tc (SQLITE_ERROR)` — D1's Workers Binding API does not support outer table alias references inside a correlated subquery used in a JOIN ON clause. This caused every `/block_detail` request to throw an exception, so `on_fetch`'s outer try/except caught it and rendered both cards as fallback (empty). Replaced with two separate simple queries: (1) fetch TMS records with no JOIN, (2) fetch LT enrichment with an exact `(tc, pfx, block)` match, falling back to a `postal_code` match. Results are merged in Python. KV fallback unchanged (fires only when D1 returns zero TMS rows).

---

## v1.3.7.3 – Block detail KV fallback (D1 empty guard)

### Changes made

**`src/entry.py`**

- **`_d1_load_block()` — KV fallback**: If D1 returns no rows for the requested block (e.g. D1 was wiped by an earlier failed `_d1_write` and hasn't been re-synced yet), the function now falls back to `cached_data` in KV. It filters the KV payload in-memory by `(TC_Display, Pfx, Block)` and returns matching records with TMS fields populated and LT enrichment fields left empty. This ensures the TMS Alarm card always shows data whenever the block is in the active alarm list, even before D1 is repopulated. LT Enrichment fields become available after the next successful sync writes to D1.

---

## v1.3.7.2 – Block detail page + postcode-fallback LT JOIN

### Bug fix (patch)

**`src/entry.py`**

- **`_status_int(v)`**: New helper that safely converts any TMS Status value to an integer. The previous `int(r.get("Status", 1) or 1)` call raised `ValueError` when the TMS API returned `"SET"` (string), causing the entire `_d1_write()` list comprehension to abort. D1 was left empty after the `DELETE` but before any inserts, so `_d1_load_block()` always returned `[]` — the block detail page showed empty/fallback content in both cards despite the main dashboard working (it fell back to KV). All active alarms now write correctly as `status = 2` (SET); `"NORMAL"` / `"OK"` / `"CLEAR"` map to `status = 1`.

**`src/block_detail.py`**

- TMS Alarm fallback card now includes the `hdr-tms` header, consistent with the Lift Talk Enrichment fallback card.

### Changes made

**`src/block_detail.py`** *(new)*

- New Worker module that renders `/block_detail?tc=&pfx=&block=` as a full HTML page.
- Displays two sections: **TMS Alarm** card(s) (one per RBE: COMF / IOF) and **Lift Talk Enrichment** card.
- TMS fields shown: TC, Pfx, Block, Lift, LCOY, Postcode, Status Date, Status.
- LT fields shown: Town Council, Postal Code (LT), Full Address, Lift Names, Interface, LSS.
- Address in header links to OneMap for the block.
- Responsive Bootstrap 5 layout; no JavaScript required.

**`src/entry.py`**

- **`GET /block_detail`**: New route — parses `tc`, `pfx`, `block` query params, queries D1 via `_d1_load_block()`, delegates rendering to `block_detail.render_html()`.
- **`_d1_load_block(env, tc, pfx, block)`**: New helper. Queries `records` LEFT JOIN `masterlist_lt` for a single block (both RBEs). Includes `lt_postal_code` separately so the detail page can show TMS postcode and LT postal code side-by-side.
- **`_d1_load()` and `_d1_load_block()` — postcode-fallback JOIN**: The LEFT JOIN now uses a correlated subquery that tries an exact `(tc, pfx, block)` match first; if none exists, falls back to `postal_code = r.postcode`. This handles TC/Pfx mismatches between TMS and Lift Talk (e.g. TMS `YS Y 833 / 760833` ↔ LT `NS Y 833 / 760833`). TMS tc/pfx always remain authoritative in the display.
- **Block column clickable**: Each block number in the main table is now a link that opens `/block_detail` in a new tab.
- **`_parse_qs(url)`**: New helper for URL query-string decoding (handles `%XX` and `+`), no stdlib dependency.

---

## v1.3.7.1 – Lift Talk MasterList enrichment via D1 JOIN

### Changes made

**`migrations/0002_masterlist_lt.sql`** *(new)*

- New table `masterlist_lt` (unique per `tc + pfx + block`): stores Lift Talk MasterList fields — `town_council`, `full_add`, `postal_code`, `lift_names_all`, `interface`, `lss`.

**`scripts/upload_lt.py`** *(new)*

- One-time enrichment script. Reads `Lift Talk - MasterList.xlsx` (columns: Town_Council, town_council_code, Pre, block, postal_code, Lift Names-All, LSS, Interface, Full Add) and POSTs to `/api/lt/upload` in batches of 200.
- Run with `ELTI_UPDATE_TOKEN=<token> python -m scripts.upload_lt`.

**`src/entry.py`**

- **`POST /api/lt/upload`**: New auth-guarded endpoint. Accepts `{"records": [...]}` and upserts into `masterlist_lt` (batch INSERT OR REPLACE, 100 per D1 batch).
- **`_d1_load()`**: Query now LEFT JOINs `records` with `masterlist_lt` on `(tc, pfx, block)`. Enrichment fields (`Town_Council`, `Full_Add`, `Lift_Names_All`, `Interface`, `LSS`) are added to each record in the JSON payload. `postcode` uses `COALESCE(NULLIF(m.postal_code,''), r.postcode)` — LT postal code takes priority, falls back to OneMap-derived postcode (fixes blocks like HB B 415 that previously had empty postcode).

**Match key**: `town_council_code = TC = tc`, `Pre = Pfx = pfx`, `block = Block = block`

---

## v1.3.7.0 – Migrate data store from KV to Cloudflare D1 (SQLite)

### Changes made

**`wrangler.toml`**

- Added `[[d1_databases]]` binding `elti_db` (database `elti-db`, region APAC/SIN).

**`migrations/0001_init.sql`** *(new)*

- Schema: `records` table (one row per TC+Pfx+Block+RBE alarm, UNIQUE constraint); `meta` table (key-value scalars: `last_updated`); `mask` table (reserved for future postcode mask migration).

**`src/entry.py`**

- **`_d1_load(env)`**: Reads all alarm records from D1 `records` table + `last_updated` from `meta`. Builds the same JSON payload structure the frontend expects. Returns `None` if D1 is empty, triggering KV fallback.
- **`_d1_write(env, data)`**: Called on every `/update` push. Clears existing rows (`DELETE FROM records`), then batch-inserts new records in chunks of 100 (D1 batch limit). Updates `meta.last_updated`. Also writes the KV backup so a KV fallback is always available.
- **`_dv(row, key)`**: Safe row getter — tries dict-key access first, falls back to attribute access (handles both Python dict and JS proxy rows from D1).
- **GET `/`**: Tries `_d1_load()` first; falls back to KV `cached_data` if D1 is empty or errors. All existing frontend features (COMF/IOF toggle, TC filter, sort, mask, OneMap link, Route Map) unchanged.
- **POST `/update`**: Now calls `_d1_write()` in addition to the KV write. Response now includes `records` count.
- Data source priority: **D1 (primary) → KV (fallback)**. KV is always kept in sync as a backup.

---

## v1.3.6.10 – Fix TMS SSL verification regression

### Changes made

**`scripts/tms_api.py`**

- **Restored `verify=False` for TMS API client**: The TMS server (Surbana internal system) uses a corporate intermediate certificate not trusted by the GitHub Actions runner CA bundle. Removing `verify=False` in v1.3.6.8 caused `[SSL: CERTIFICATE_VERIFY_FAILED]` and broke every sync. OneMap requests (public cert) correctly keep SSL verification enabled.

---

## v1.3.6.9 – Postcode lookup reliability improvements

### Changes made

**`scripts/sync_tms.py`**

- **Retry on transient errors**: Replaced the inline `httpx.get()` call with `_om_get()` helper that retries once on any network/HTTP error before giving up. Previously a silent `except Exception: return key, ""` caused 13 of the 14 postcode failures — the addresses exist in OneMap but requests timed out during concurrent lookups and were silently dropped.
- **Block alpha-suffix fallback**: When the `"block street"` query returns 0 results and the block ends with a letter suffix (e.g. `"54A"`), retries with the numeric-only form (`"54 TELOK BLANGAH DRIVE"`). Fixes `TX T 54A TELOK BLANGAH DRIVE` — OneMap only indexes it as block 54, returning POSTAL=100054.
- **Street-only fallback**: If both block-based queries return 0 results, falls back to a street-only search as a last resort, using `_choose_postal` scoring to pick the best block match.

Root-cause analysis (14 empty-postcode rows found in live data):
- 13/14: OneMap has valid data; failures were transient HTTP errors swallowed silently.
- 1/14 (`54A TELOK BLANGAH DRIVE`): block suffix `"A"` not in OneMap; stripping to `"54"` returns POSTAL=100054.

---

## v1.3.6.8 – Postcode lookup bug fixes + security hardening

### Changes made

**`scripts/sync_tms.py`**

- **Bug fix – BLK prefix regex**: The old regex `\b(?:BLK|BLOCK)\b` failed to strip the prefix in formats like `"BLK123"` (no space) because both `K` and `1` are word characters — no word boundary between them. Replaced with `(?:BLK|BLOCK)\s*` (no leading boundary required) via a shared `_strip_blk()` helper. Now handles `"BLK 123"`, `"BLK123"`, and `"BLOCK 123"` uniformly.
- **Bug fix – block scoring in `_choose_postal`**: `ub` was compared against OneMap's `BLK_NO` (e.g. `"123"`) while `ub` still held the raw TMS value (`"BLK 123"`). They never matched, losing the +10 block-match bonus and risking wrong postal code selection on streets with multiple blocks. Now `ub` is normalized via `_strip_blk()` before comparison.
- **Initial no-result fallback**: When the `"block street"` query returns 0 results, falls back to a street-only search. (Expanded to 3-tier with retry in v1.3.6.9.)
- **Removed `verify=False`** on OneMap requests: OneMap is a public Singapore government API with valid CA-signed certificates; SSL verification is appropriate.

**`scripts/tms_api.py`**

- **Removed `verify=False`** from `httpx.Client` — later found to break TMS sync (reverted in v1.3.6.10; TMS server uses a corporate cert not trusted by GitHub Actions).

**`src/entry.py`**

- **Auth guard on `/api/token`**: The token endpoint now requires the `X-Update-Token` header, consistent with all other protected endpoints. Previously it was publicly accessible.
- **Error response hardening**: The global exception handler no longer echoes the raw exception message (`str(e)`) in the 500 response body; returns the generic `"Internal server error"` string and logs detail server-side only.

**`src/onemap.py`**

- **Removed hardcoded credentials**: `get_token()` previously fell back to hardcoded email/password when secrets were absent. Now returns `""` and logs a warning, preventing accidental credential exposure.

---

## v1.3.6.7 – No. column + TMS sync reliability fix

### Changes made

**`src/entry.py`**

- **No. column**: Added a new `No.` column to the left of `Mask` in the alarm table. Displays the 1-based row number for the current filtered view. Static label (no sort button), re-numbers automatically whenever the table is filtered or sorted.

**`scripts/tms_auth.py`**

- **Login redirect detection**: After clicking Login, now waits for the URL to actually leave `/login` (up to 10 s) before proceeding. Previously it blindly waited 4 s — the failure log showed `URL: ***/login`, suggesting the redirect didn't complete and the alarm page loaded unauthenticated.
- **Longer post-navigation wait**: Increased from 3 s → 5 s to give Angular components more time to render.
- **Broader fallback selector**: Added bare `app-searchable-dropdown` alongside the existing ID/class selectors, in case the wrapping element was renamed.
- **Dropdown timeout**: Increased from 10 s → 20 s.
- **Screenshot on failure**: When the dropdown is not found, saves a full-page screenshot to `$RUNNER_TEMP/tms_dropdown_fail.png` and prints the current URL and page title for diagnosis.

**`.github/workflows/sync_tms.yml`**

- Added `Upload debug screenshots` step (runs on failure) that uploads any `tms_*.png` from `$RUNNER_TEMP` as a downloadable GitHub Actions artifact (`tms-debug-screenshots`).

**`.gitignore`**

- Added `README.md` so this local changelog is never committed to the repository.

---

## v1.3.6.6 – Cross-device mask sync via Cloudflare KV

## v1.3.6.5 – Responsive layout for mobile/tablet, mask counts refresh on load

## v1.3.6.4 – Show current/total counts in all 3 buttons, sync to map page

## v1.3.6.3 – Checkbox sort button, Route count, live count update on check

## v1.3.6.2 – Guard against stale localStorage format on init

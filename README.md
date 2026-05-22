# ELTI – EP1W LMD Telemetry Insight

## 版本记录

---

### v1.4.0 — 2026-05-22

#### 新增功能：ROUTE 地图页

##### 功能说明

1. **OneMap 自动续期**：Worker 使用存储的 `ONEMAP_EMAIL` / `ONEMAP_PASSWORD` 密钥自动获取并缓存 OneMap access_token（有效期 72 小时，到期自动刷新，存储于 KV）
2. **ROUTE 按钮**：在 COMF / IOF 右侧新增 ROUTE 按钮，配色 `rgb(175, 244, 43)`
3. **地图页（`/route`）**：点击 ROUTE 按钮在新标签页打开全屏 OneMap 地图，标记所有当前 COMF 和 IOF 告警点位
4. **配色规则与主页一致**：COMF = 紫色 `rgb(153, 87, 255)`，IOF = 青色 `rgb(34, 213, 254)`
5. **响应式设计**：适配手机、平板、桌面，地图始终占满剩余视口，控件自动调整大小

##### 地图页特性

- 使用 OneMap 官方瓦片（`Default/{z}/{x}/{y}.png`）
- 地址逐批并发 geocoding（8 个并发，每批间隔 60 ms），带进度条
- 加载完成后自动 fitBounds 至所有点位
- 左下角 COMF / IOF 图层开关（点击可隐藏/显示）
- 右上角图例
- 点击圆形标记弹出详情（TC、Block、Address、Lift、LCOY、Status Date、Status）

##### 部署说明

使用 OneMap 自动续期功能需在 Cloudflare Worker 中设置两个密钥：

```bash
wrangler secret put ONEMAP_EMAIL
wrangler secret put ONEMAP_PASSWORD
```

若未设置密钥，`/route` 页面仍可正常使用（geocoding 使用无鉴权模式，速率限制较严）。

##### 变更文件

| 文件 | 说明 |
|------|------|
| `src/entry.py` | 新增 `ROUTE_HTML`、`_get_onemap_token()`、`/route` 路由；版本升级至 **1.4.0** |
| `README.md` | 新增 v1.4.0 版本记录 |

---

### v1.3.4.0 — 2026-05-22

#### 性能优化结果

| 指标 | 旧版 | 新版 |
|------|------|------|
| 总运行时间 | 2m54s | **1m01s** |
| 脚本本身执行 | ~2.5 分钟 | **~1 秒**（几乎瞬间完成） |
| 获取方式 | Playwright 逐页翻页 × 2 | 单次 REST API 调用 × 2（并行） |

#### 核心优化原理（来自 LMD Alarm Table / TMS_API.md）

1. **Token 拦截**：浏览器只用于登录 + 拦截第一个 API 请求，自动捕获 Bearer token 和 `x-*-for` context headers
2. **直连 REST API**：`isPaginated=false` 一次性返回所有记录，消除了所有翻页循环和 `wait_for_timeout` 等待
3. **并行抓取**：COMF 和 IOF 通过 `ThreadPoolExecutor` 并发请求

#### 新文件结构

| 文件 | 说明 |
|------|------|
| `scripts/tms_auth.py` | 浏览器登录 + API token 捕获 |
| `scripts/tms_api.py` | 直连 REST API 客户端（并行） |
| `scripts/tms_transform.py` | EP1WM 过滤 + 数据合并 |
| `scripts/sync_tms.py` | 精简入口 |
| `scripts/__init__.py` | 使 scripts 成为 Python package |
| `src/entry.py` | 版本升级至 **1.3.4.0** |
| `.github/workflows/sync_tms.yml` | 改用 `python -m scripts.sync_tms` |

#### 实际同步结果（首次验证）

- COMF：221 条原始 → 47 条（EP1WM + 合并）
- IOF：821 条原始 → 244 条（EP1WM + 合并）
- 共推送 **291 条**记录 → Worker HTTP 200 ✓

---

### v1.3.3.4 — 2026-05-22

- CI: trigger deploy with Node 24 workflow

---

### v1.3.3.3 — 2026-05-22

- Security: fix API timeout, CSP headers, URL validation, input guards, date regex

---

### v1.3.3.2 — 2026-05-22

- Security: fix TC onclick injection and innerHTML XSS

---

### v1.3.3.1 — 2026-05-22

- Security: fix server-side script injection in `<script>` block

# ELTI – EP1W LMD Telemetry Insight

## 版本记录

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

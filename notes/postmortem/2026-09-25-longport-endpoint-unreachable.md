# 2026-09-25 — 启动"卡住一动不动"：端点直连不可达 + 失败分支整读 3.36 GB 日志

## 症状

`.\.venv\Scripts\python.exe manage.py start-all` 输出到

```text
[start-all] Backend readiness gate: /health timeout=180s
[start-all] Backend log tail:
```

之后长时间无任何输出（KAI 描述"一动不动"）。后端从未起起来。

## 时间线（美国东部时间 EDT）

| 时刻 | 事件 |
|---|---|
| 08:21:44 | `mihomo-windows-386.exe`（pid 2012，`MAOMAOYUNAPP`）启动；**TUN 为关闭状态** |
| 09:25:08 | 计划任务 `MON-FRI 09:25` 触发，后端 `[BOOT] mode=strict` |
| 09:27:48 | KAI 手动 `start-all`，后端 `[BOOT]` pid=21476 |
| 09:27:54 | 后端日志 `[SubscriptionManager] Quote runtime connected.` |
| **09:28:15** | `[WARNING] [RustQuoteRuntime] rest_quote failed on endpoint profile 'primary' (http=https://openapi.longportapp.com)` |
| **09:28:15** | lifespan 抛 `RuntimeError: startup connectivity probe failed ...` → `Application startup failed. Exiting.` |
| 09:28:15–≈09:30:48 | `start-all` 盲等 `/health` 满 180 s（不检查子进程是否已死） |
| ≈09:30:48 | 打印 `Backend log tail:` → 开始整读 3.36 GB 日志 → 卡住 |

后端进程此后**已退出**（诊断时 `tasklist` 无 `python.exe`）；Redis（`memurai.exe` :6380）与前端（2 × `node.exe`）仍在。

## 关键证据

| 检查项 | 命令 | 结果 |
|---|---|---|
| 端点直连 | `curl --noproxy '*' https://openapi.longportapp.com/v2/socket/token` | `code=000`，12.0 s 超时 |
| 端点走 mihomo | `curl -x http://127.0.0.1:10090 ...` 同上 | **`code=401`，1.47 s**（服务活着，缺鉴权） |
| `.cn` 直连 | `curl --noproxy '*' https://openapi.longportapp.cn/v2/socket/token` | **`code=401`，0.41 s** |
| DNS（114DNS） | `nslookup openapi.longportapp.com` | `128.242.250.148`（Facebook 段）+ IPv6 `…:face:b00c:…` |
| DNS（8.8.8.8） | 同上 | `104.244.43.6`（Twitter 段） |
| DNS（223.5.5.5） | 同上 | `202.160.129.37` |
| 备选 profile 域名 | `nslookup openapi.longbridge.com` | `2600:9000:…`（CloudFront），直连仍 `code=000` |
| 代理进程 | `tasklist` | `mihomo-windows-386.exe` pid 2012；`sandbox-cli.exe` pid 17928 |
| 系统代理 | `HKCU:\…\Internet Settings` | `ProxyEnable=1`，`ProxyServer=127.0.0.1:10090` |
| 用户/系统环境变量 | `HKCU\Environment` / `HKLM\…\Session Manager\Environment` | **均无 `*_proxy`** |
| mihomo 运行态 | `GET http://127.0.0.1:9790/configs` | `mode=rule`，**`tun.enable=false`**，`mixed-port=10090` |
| TUN 网卡 | `ipconfig` | 只有 Teredo，**无 TUN 适配器** |
| 本机 DNS 服务器 | `Get-DnsClientServerAddress` | WLAN → `114.114.114.114, 61.139.2.69` |
| 项目内代理约定 | `.cargo/config.toml` | `[http] proxy = "http://127.0.0.1:10090"` |
| 上一次成功 | `grep "probe passed"` 日志 | **2026-09-24 12:52:42**，`profile=primary`，`spot=768.13`（共 92 次通过 / 15 次失败） |

### 非空转 A/B/C/D 探针（同一份原生网关 + 同一套凭证，只翻一个变量）

探针：`tmp/_probe_proxy_ab.py`（调 `l0_rust.quote_api_rest_quote_rows(gw, ["SPY.US"])`）

| 臂 | 变量 | 结果 | 耗时 |
|---|---|---|---|
| A | 无代理环境变量（= KAI 的 cmd） | **FAIL** `error sending request for url (…longportapp.com/v2/socket/token)` | 21.06 s |
| B | `HTTPS_PROXY=http://127.0.0.1:10090`（mihomo） | **FAIL** `connect timeout` | 5.31 s |
| C | `HTTPS_PROXY=http://127.0.0.1:1`（死端口） | FAIL `error sending request` | 2.01 s |
| D | 只改端点 URL 为 `.cn`，无代理 | **OK rows=1 `last_done=769.484`** | 2.53 s |

臂 A 的报错与 09:28:15 生产日志**逐字一致**，即现场已复现。

### 端点数据保真（`tmp/_probe_row_dump.py`，`.cn`）

```text
US       | LV1 Real-time Quotes
USOption | LV1 Real-time Quotes
CN       | LV1 Real-time Quotes
HK       | LV2 Advanced Quotes, Real-time Quotes
last_done = 769.59   timestamp = 1790344082
turnover  = 2298207930.542   volume = 2988080
```

`timestamp=1790344082` → `2026-09-25T13:48:02Z`，与本机取数时刻（`13:47:59Z`）同秒级 ⇒ **实时，非延迟**；账号对 US/USOption 持有 LV1 实时权限。

### 失败分支的开销（`tmp/_bench_naive_read.py`）

```text
file_size_bytes=3,360,960,390
read_text   :   31.28s  chars=3,331,968,314
splitlines  :   11.82s  lines=27,938,231
slice[-40:] :    0.00s
TOTAL       :   43.11s
```

## 根因

### 层 1 — 端点直连不可达（真正原因）

`openapi.longportapp.com` 及其 `openapi-quote/-trade` 一族在本机网络**被污染**：三个公共 DNS 返回
互不相同的境外无关 IP，IPv6 带 Facebook 标记 `face:b00c`。项目默认端点
（`shared/config/api_credentials.py:32/36/40`）全部指向该域名族，而 `.env` 未做覆盖。

后端 lifespan 的硬性连通性探针（`shared/services/l0_runtime/source/runtime/bootstrap.py:43`
`_startup_connectivity_probe`）拉 `SPY.US` 报价失败即抛错，且该探针**被策略禁止关闭**
（同文件 49–53 行：`strict_connectivity=false is forbidden by runtime policy`）。

**加代理环境变量不是修法**：臂 B 实测仍 FAIL。切 `.cn` 端点是**已实测可用**的修法（臂 D）。

### 层 2 — 失败分支整读日志（"一动不动"的直接来源）

`infra/ops_cli/start_all.py:177`：

```python
print("\n".join(log_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-40:]))
```

把 3.36 GB / 2793 万行**整个读进内存**再取末 40 行 —— 实测 **43.11 s**、峰值内存数 GB。
且 `_wait_backend_healthy`（同文件 77–83 行）只轮询 `/health`，**不检查子进程是否已退出**，
所以即便后端 09:28:15 就死了，仍会空等到 09:30:48。

⇒ 用户观感 = **静默 180 s + 卡死 43 s**。即使层 1 修好，只要后端再次启动失败，这里照样卡。

### 层 3 — 日志无轮转

`infra/ops_cli/start_backend.py:185-193` 以 `open(..., "a")` 追加写、无轮转，
自 2026-04-22 累积到 3.36 GB。这是层 2 从"瞬间"恶化成"43 秒"的前提。

## 修复

### 1. 层 1：打开 mihomo 的 TUN（KAI 手动，环境侧，后端零改动）

10:44 打开后实测：

| 检查项 | 结果 |
|---|---|
| TUN 网卡 | `tun_enable=True`，`device=Meta`，IPv4 `198.18.0.0/30`，网关 `198.18.0.1` |
| 端点直连 | `openapi.longportapp.com/v2/socket/token` → **`code=401`，0.27 s** |
| 原生网关臂 A 复测 | **OK `last_done=767.84`，3.25 s** |

**非空转**：同一份代码、同一套凭证、同一端点（`.com`）、同样无代理环境变量，
**只翻 TUN 一个开关** ⇒ `FAIL (21.06 s)` → `OK (3.25 s)`。

**因此没有改任何端点配置** —— `shared/config/api_credentials.py` 的默认值保持 `.com`。
`.cn` 方案（上文臂 D）作为备用路径保留记录，未启用。

### 2. 层 2：`start_all.py` 的失败分支改为有界读尾部

`infra/ops_cli/common.py` 新增 `read_tail_lines(path, max_lines, *, max_bytes=256 KiB)`：
只从文件尾读一个有界字节窗口，丢弃窗口首行的截断片段。
`start_all.py` 的三处日志尾部打印（Redis / Backend / Frontend）全部改用它。

新增回归测试 `infra/ops_cli/test_common.py`（7 例），其中
`test_read_tail_lines_does_not_scan_from_the_start` 用"1 MiB 首行 + 500 短行"钉住
"绝不从文件头开始读"这一性质。

### 3. 层 3：轮转既有超长日志

`logs/backend_runtime.current.log`（3.36 GB）改名为
`logs/backend_runtime.current.log.1`（**原样保留，未删除**），current 槽位重新开始。
`main.py` 的日志级别问题见"遗留"。

## 验证

| 验证 | 方法 | 结果 |
|---|---|---|
| 后端可启动 | `manage.py start-all` | `Backend is healthy (/health=200) on port 8001.` |
| 端点恢复 | 后端日志 | `Startup connectivity probe passed: symbol=SPY.US rows=1 spot=767.7200 profile=primary endpoint=https://openapi.longportapp.com` |
| 数据链路真的活 | 后端日志 | `[L3-PAYLOAD] tick_id=7 … spot=768.205`；`[MarketEventBridge] Streaming 2 event for SPY260925P771000.US (bid=3.11 ask=3.12)`；`GET /health 200 OK` |
| 三件套就绪 | `start-all` 末尾 | `Redis 6380 True / Backend 8001 True / Frontend 5173 True`，`All services are up.` |
| 卡死修复有效 | `tmp/_bench_tail_fix.py`（同一份 3.36 GB 文件，新旧实现对比） | OLD **81.70 s** → NEW **0.010 s**（**8198×**），`IDENTICAL_CONTENT=True`（末 40 行逐行一致） |
| 回归 | `pytest infra/ops_cli/test_common.py infra/ops_cli/test_start_all.py -q` | **19 passed** |

## 遗留

- **服务无法从自动化会话持久启动**：`start-all` 拉起的 backend / frontend 会随发起它的
  Windows Job Object 一起被回收（`subprocess.Popen(start_new_session=True)` 在 Windows 上是
  POSIX-only，挡不住）。实测：启动后 `/health=200`、`L3-PAYLOAD` 正常，任务一结束
  `python.exe` 与新建的 `node.exe` 同时消失（Redis 作为服务存活）。
  ⇒ **长驻服务仍必须在交互式终端里启动**（同 2026-09-24 复盘结论）。
  `schtasks` 在本沙箱被安全策略禁止，无法代为触发 `OptionV4-StartAll-PreOpen`。
- **`main.py:13-17` 硬编码 `logging.DEBUG`**，而 `shared/config/api_credentials.py:100`
  的 `log_level`（默认 `INFO`）**声明后从未被使用** ⇒ 3.36 GB 日志的直接来源。
  修法：`level=settings.log_level.upper()`。**本次未改**（会显著降低日志量，属行为变更，需 KAI 裁定）。
- **`_wait_backend_healthy`（`start_all.py:77-83`）不检查子进程是否已退出**：
  后端 09:28:15 就死了，仍空等到 09:30:48（满 180 s）。这是"静默 180 s"的来源。
  **本次未改**（属行为变更，需要把 pid 从 `run_start_backend` 透出）。
- **探针无回归保护**：`tmp/_probe_proxy_ab.py`、`tmp/_probe_row_dump.py`、
  `tmp/_bench_naive_read.py`、`tmp/_bench_tail_fix.py` 均为一次性探针；
  项目内**没有**端点可达性的常驻检查器（`read_tail_lines` 已有单测）。
- **文档失真**：`最新的启动步骤文档.md` §9.4「Backend strict 启动失败」只提"LongPort 凭据是否有效"，
  **未提网络/代理/端点可达性**；§2.12 说 `--verify-only` 只查端口，但 `start_all.py:337`
  现已额外要求 `/health==200`。
- **`.cn` 备选路径未做 WS 长连接验证**（只验到 REST 报价 + `/v2/socket/token` 返回 401）。
- **沙箱环境变量干扰**：诊断 shell 里 `https_proxy/http_proxy/HTTPS_PROXY/HTTP_PROXY=127.0.0.1:57026`
  来自 `sandbox-cli.exe`（WorkBuddy 沙箱），**不在 KAI 的 cmd 环境**，与本次故障无关。

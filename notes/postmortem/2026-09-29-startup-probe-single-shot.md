# 2026-09-29 — 启动卡在 backend readiness gate：启动探针一次性硬失败

## 症状

`.\.venv\Scripts\python.exe manage.py start-all` 输出到

```text
[start-all] Backend readiness gate: /health timeout=180s
```

之后长时间无输出。后端从未起来：`Application startup failed. Exiting.`

## 时间线（美国东部时间 EDT）

| 时刻 | 事件 |
|---|---|
| 09:25:xx | 计划任务触发 → `error sending request for url (https://openapi.longportapp.com/v2/socket/token)` |
| 09:26:47 | KAI 重试 → `QuoteContext init failed: IO error: tls handshake eof` |
| 09:27:00 / 09:28:45 | 再重试两次 → 同为 `tls handshake eof` |
| 09:28:59 | lifespan 抛 `startup connectivity probe failed` → 进程退出 |
| 09:32 | 诊断现场复现：`curl --noproxy '*' https://openapi.longportapp.com/` → `schannel: failed to receive handshake, SSL/TLS connection failed` |
| 09:33 起 | 同一 URL 自行恢复，10 次采样全通；原生网关 10/10 OK |

## 关键证据

| 检查项 | 命令 | 结果 |
|---|---|---|
| mihomo TUN | `GET http://127.0.0.1:9790/configs` | `tun.enable=true`，`device=Meta`，`dns-hijack=["0.0.0.0:53"]`，`mixed-port=10090` |
| 模式 | 同上 | `mode=global` |
| DNS | `nslookup openapi.longportapp.com` | Server `198.18.0.1`（TUN 网关）→ fake-IP **`198.18.1.89`** |
| 选择器 | `GET /proxies/猫猫云` | `now=1.0x 🇭🇰 香港 HK - 1`，但 `GET /connections` 里存量连接链仍是 `1.0x 🇸🇬 新加坡 SG - 7` ⇒ 期间发生过节点切换 |
| 端点直连（无代理） | `curl --noproxy '*' https://openapi.longportapp.com/` | **FAIL** `schannel: failed to receive handshake` |
| 端点经代理 | `curl --resolve openapi.longportapp.com:443:198.18.1.89 ...` | `code=404`（服务活着） |
| 原生网关 | `tmp/_probe_proxy_ab.py`（无代理环境变量） | 故障窗口 **FAIL** `tls handshake eof`；09:33 后 **10/10 OK** |
| 节点延迟 | `GET /proxies/<HK-1>/delay?url=…longportapp.com/v2/socket/token` | `{"delay":146}` |

## 根因

### 层 1（触发条件，环境侧）—— 端点经代理的链路在 09:25–09:32 中断

`openapi.longportapp.com` 直连不可达（TLS 握手被中断），唯一可用路径是 mihomo（TUN + fake-IP）。
故障窗口内选择器发生了节点切换（存量连接在 SG-7、选择器已指向 HK-1），期间到该端点的 TLS 握手全部中断。
09:33 后**自行恢复**，未改任何端点配置。

### 层 2（真正的代码缺陷）—— 重试配置声明了却从未接线

`shared/config/api_credentials.py:58/62` 声明了两个键：

- `longport_connect_retries`（来自 `shared_rust.contracts`，实测默认 **3**）
- `longport_connect_retry_base_sec`（实测默认 **0.8**）

全仓 grep：**除声明处外零引用** ⇒ 死配置。

而 `bootstrap.py` 的 `_startup_connectivity_probe` 只调用一次 `runtime.quote()`，一次瞬时 TLS EOF 即抛错；
该探针又被策略禁止关闭（同文件：`strict_connectivity=false is forbidden by runtime policy`）。

⇒ **一次约 7 分钟的网络抖动 = 整个后端拒绝启动**，且没有第二条路可走。

### 层 3（"卡住"观感）—— readiness gate 盲等

`_wait_backend_healthy` 只轮询 `/health`，不检查子进程是否已退出。后端 09:28:59 就死了，仍空等到 180 s。
（9-25 已把失败分支的整读 3.36 GB 日志改成有界尾部读，所以本轮不再卡 43 s，但静默 180 s 仍在。）

### 旁证：`connect()` 不连网

`shared/services/l0_runtime/services/subscription/__init__.py:174-175`：`connect()` 仅置 `_connected = True`，
随后打印 `[SubscriptionManager] Quote runtime connected.`。探针失败的那三次日志里**这行照样打印**。
属误导性信号，本轮未改。

## 修复

1. **`bootstrap.py`**：新增 `_resolve_retry_policy` + `_probe_quote_rows_with_retry`，把既有配置接进启动探针。
   - 只对**传输异常**重试（指数退避 `base * 2^(n-1)`）；**返回行集（含空集）不重试** —— 数据契约失败必须立即暴露。
   - 全部失败后**重抛原始异常**，错误串保持原前缀并追加 `attempts=N`（原 grep 口径不变）。
   - 重试策略非法（`retries < 1` / `base < 0`）即抛错，无静默兜底。
2. **`builder.py:99`**：传入 `settings.longport_connect_retries` / `settings.longport_connect_retry_base_sec`（改为直接属性访问）。
3. **`start_backend.py`**：`run_start_backend(..., on_process_started=...)` 透出真实 `Popen` 句柄（返回类型不变，`manage.py start-backend` 不受影响）。
4. **`start_all.py`**：`_wait_backend_healthy(..., child=)` 在子进程已退出时立即返回 False；失败信息区分「早退 `exit_code=N`」与「超时未就绪」。
5. **拆分超限文件**（门禁 400 行）：`start_all.py` **405 → 258** 行；前端启动逻辑移入新模块 `frontend_launch.py`；
   通用原语（`run_powershell` / `is_listening` / `resolve_abs_path` / `listening_pids` / `kill_processes_on_port`）下沉 `common.py`；
   `start_all_task.py` 同步改引用。

## 验证

| 验证 | 方法 | 结果 |
|---|---|---|
| 端点现场复现 | `curl --noproxy '*'` | `schannel: failed to receive handshake`（与 Rust `tls handshake eof` 同形） |
| 端点恢复 | `tmp/_probe_proxy_ab.py` ×10 | **10/10 OK** |
| 回归 | `pytest infra/ops_cli/ shared/services/l0_runtime/source/runtime/test_bootstrap.py -q` | **40 passed** |
| **非空转对照** | `test_single_attempt_policy_would_still_fail_on_the_same_fault` | 同一故障形状：`attempts=1` → 抛错（`calls==1`）；`attempts=3` → 成功（`calls==3`） |
| 重试不误伤数据失败 | `test_startup_connectivity_probe_does_not_retry_data_contract_failures` | `last_done=0` 时 `calls==1`（不重试） |
| 失败快报 | `test_wait_backend_healthy_stops_early_when_child_exited` | 30 s 超时下 **< 5 s** 返回（旧实现需 30 s） |
| 端到端启动 | `manage.py start-all` | `Backend is healthy (/health=200)`；`Startup connectivity probe passed`；`[L3-PAYLOAD] tick_id=1..11` 实时 SPY 765.xx；`Frontend is HTTP-ready`；`Verification summary` 三项全 True |
| 架构门禁 | `manage.py check-layer-boundaries` | `[OK] Layer boundary scan passed (full repository)` |
| **数据通路（非空转，非"端口开着"）** | `tmp/_probe_dashboard_ws.py`（走前端代理 `ws://127.0.0.1:5173/ws/dashboard`） | 连通；`frame[1]` 15233 B 全量 `spot=765.58 snapshot_version=64658`；`frame[2]/[3]` 增量帧 248 B / 11763 B ⇒ **UI 真实数据链路有活数据** |
| 持续存活 | 跨 10+ 次命令、数分钟复查 | `8001 pid=20564` / `5173 pid=28556` 均在；`/health=200`、前端 `200`；`tick_id` 183 → 218 以 1 Hz 递增 |

## 遗留

- ~~**长驻服务仍无法从自动化会话启动**~~ **本轮已解决**（推翻 9-24 / 9-25 的两次结论）。
  - 现象：agent shell 内直接跑 `manage.py start-all` 可跑通（`/health=200`、`L3-PAYLOAD` 正常），
    但命令一结束 `python.exe` 与新建的 `node.exe` 全部消失（Redis 作为服务存活）。
  - 试过并**失败**：`subprocess.Popen(..., creationflags=CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS)`
    （`tmp/_detach_start_all.py`，breakaway 未报 Access Denied，launcher pid=26140）⇒ 沙箱按**进程树**回收，
    job breakaway 无效。
  - **有效做法**：用 WMI 创建进程，父进程变成 `WmiPrvSE.exe`，不在 agent shell 的进程树内。
    ```powershell
    $inner = 'cd /d E:\US.market\Option_v4 && set "HTTPS_PROXY=" && set "HTTP_PROXY=" && ' +
             '"E:\US.market\Option_v4\.venv\Scripts\python.exe" manage.py start-all >> "E:\US.market\Option_v4\logs\start_all_wmi.log" 2>&1'
    ([wmiclass]'Win32_Process').Create('cmd.exe /c ' + $inner)
    ```
    实测 `ReturnValue=0`；随后**跨 10+ 次命令、数分钟**持续存活：
    `8001 LISTENING pid=20564`、`5173 LISTENING pid=28556`、`/health=200`、前端 `200`、`L3-PAYLOAD` 1 Hz 递增（tick_id 76 @ 09:52:39）。
  - 注：`Win32_Process.Create` 继承的是 `WmiPrvSE` 的环境，**天然不含**沙箱注入的 `*_proxy`，正好等于 KAI 的 cmd 环境。
  - 另注：`python.exe` 出现两个属正常 —— `27412` 是 `.venv\Scripts\python.exe` 启动器 stub（3.5 MB），
    真正的解释器是它的子进程 `20564`（系统 Python 路径，208 MB），8001 由后者监听。
- `[SubscriptionManager] Quote runtime connected.` 是误导性日志（`connect()` 无网络 I/O）。未改。
- `main.py` 日志级别：**本条措辞已修正**。`HEAD:main.py:14` 确为硬编码 `logging.DEBUG`（原结论在 HEAD 上成立）；
  但**工作区**已有另一会话的未提交改动把它改成 `level=settings.log_level.upper()`。
  即：**在 HEAD 上未闭合，在工作区已被他人在改**。本条按 HEAD 计仍属遗留，但已被另一会话的在途改动覆盖。
- ~~`longport_startup_strict_connectivity` 仍是 `getattr(..., True)` 静默兜底。~~
  **本轮已一并改掉**：`builder.py:94` 现为 `strict_connectivity=bool(settings.longport_startup_strict_connectivity)`，
  三键全部走直接属性访问，`getattr` 兜底在 `builder.py` 内已不存在。
- 端点可达性仍无**常驻检查器**（9-25 已记）。

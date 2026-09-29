TASK-ID: startup-probe-fix-and-log-layout
DATE: 2026-09-29
TIER: T2
STATUS: complete
CHANGE-ID: N/A:no OpenSpec change opened — fix + ops-CLI change, no contract/schema delta

STARTUP-PROOF: N/A:session began as a live incident triage (system would not start); no baseline could be
captured before the first write. The HEAD baseline was reconstructed afterwards and is recorded under
COMMAND-EVIDENCE (`git show HEAD:...`), which is evidence, not a pre-work proof.

PROPOSAL-PATH: N/A:no OpenSpec change
TASKS-PATH: N/A:no OpenSpec change
ACCEPTANCE-BUNDLE: N/A:no acceptance bundle defined for this repo
HARNESS-IMPROVEMENT: N/A:no harness change this session
FAST-FAIL-CHECK: pass — retry policy rejects `retries < 1` / `base < 0` with RuntimeError; no implicit default
NO-FALLBACK-BEHAVIOR: pass — probe re-raises the original transport exception after exhausting attempts; no
  degraded "start anyway" path was added
NO-PATCH-BANDAGE: pass — root cause fixed at the layer that owned it (dead config wired into the probe;
  readiness gate given the child handle) rather than widening the timeout
NO-COMPAT-BRANCH: N/A:no legacy branch retained
NO-ROLLBACK-PATH: N/A:no runtime rollback path involved

---

# Handoff — 启动探针一次性硬失败 + 日志按日期/启动次数归类

## 两个工作流（同一会话，同一 session root）

1. **W1 — 启动硬失败**：`manage.py start-all` 卡在 `Backend readiness gate: /health timeout=180s`。
   根因三层（网络触发 / 死配置 / 盲等），已修复并端到端验证。
2. **W2 — 日志归类**：日志输出改为 `logs/<YYYY-MM-DD>/<service>/run-<NNN>.log`，
   按「交易日 + 启动序号」两维归档，格式逐字不变。

W1 的完整复盘（症状 / 时间线 / 证据表 / 根因 / 修复 / 验证）在
`notes/postmortem/2026-09-29-startup-probe-single-shot.md`，本文件不重复其内容，只做指向。

## CHANGED-PATHS

**新增**

- `infra/ops_cli/log_layout.py` — 日志布局唯一归属（日期换算 / 目录推导 / 序号申领）
- `infra/ops_cli/frontend_launch.py` — 前端启动逻辑（W1 拆 400 行门禁时从 `start_all.py` 分出）
- `shared/services/l0_runtime/services/runtime/arrow_transport.py` — Arrow IPC 传输适配切片
  （W1 收尾时 `builder.py` 被我推到 401 行，为修复该门禁违规而切出；详见 `project_state.md`）
- `infra/ops_cli/test_log_layout.py` — 9 例
- `infra/ops_cli/test_frontend_launch.py` — 前端启动行为
- `infra/ops_cli/test_common.py` — 下沉原语的行为
- `notes/postmortem/2026-09-29-startup-probe-single-shot.md` — W1 复盘
- `notes/sessions/2026-09-29/startup-probe-fix-and-log-layout/handoff.md` — 本文件
- `notes/sessions/2026-09-29/startup-probe-fix-and-log-layout/project_state.md` — 设计取舍
- `.workbuddy-ai/memory/2026-09-29.md` — 当日工作记忆
- `C:\Users\Lenovo\.workbuddy-ai\skills\windows-detached-service-launch\SKILL.md` — 跨项目可复用技能

**修改**

- `shared/services/l0_runtime/source/runtime/bootstrap.py` — 接入重试策略（+66/-）
- `shared/services/l0_runtime/services/runtime/builder.py` — 传 `longport_connect_retries` / `..._retry_base_sec`；
  并把 `getattr(settings, "longport_startup_strict_connectivity", True)` 改为直接属性访问；
  **401 → 265 行**（Arrow 传输切片移入 `arrow_transport.py`）
- `shared/services/l0_runtime/source/runtime/test_bootstrap.py` — 扩到 8 例（含非空转对照）
- `infra/ops_cli/start_backend.py` — `on_process_started` 回调 + 日志槽位申领
- `infra/ops_cli/start_all.py` — **405 → 267 行**；子进程早退检测；三服务日志各自申领
- `infra/ops_cli/start_all_task.py` — 改引用 `common` / `frontend_launch` / `log_layout`
- `infra/ops_cli/common.py` — 下沉 `run_powershell` / `is_listening` / `resolve_abs_path` /
  `listening_pids` / `kill_processes_on_port` / `ensure_dir` / `read_tail_lines`
- `infra/ops_cli/test_start_all.py` — 参数面改为 `--log-root`
- `app/tests/test_start_backend_strict_restart.py` — **修既有红测**（见下）
- `docs/SOP/SYSTEM_OVERVIEW.md` — 取最新日志命令改为新布局
- `最新的启动步骤文档.md` — §7 重写 + §9.2/§9.4/§9.5 引用

**删除**

- 无

## COMMAND-EVIDENCE

W1 基线（HEAD，用于确认缺陷在改动前就存在）：

- `git show HEAD:infra/ops_cli/start_all.py | wc -l` → `405`（已超 400 行门禁）
- `git show HEAD:main.py | sed -n '13,17p'` → `level=logging.DEBUG`（硬编码，见 OPEN-RISKS）
- `git show HEAD:app/tests/test_start_backend_strict_restart.py` → 断言 `mod.signal.SIGTERM`；
  实现用 PowerShell `Stop-Process` ⇒ **改动前就是红的**

W1 回归：

- `PYTHONNOUSERSITE=1 ./.venv/Scripts/python.exe -m pytest infra/ops_cli/ shared/services/l0_runtime/source/runtime/test_bootstrap.py -q` → **40 passed**
- `manage.py check-layer-boundaries` → `[OK] Layer boundary scan passed (full repository)`
- `manage.py start-all` → `Backend is healthy (/health=200)`；`Startup connectivity probe passed`；
  `[L3-PAYLOAD] tick_id=1..11`（SPY 765.xx）；`Frontend is HTTP-ready`；`Verification summary` 三项全 True
- `tmp/_probe_dashboard_ws.py`（走前端代理 `ws://127.0.0.1:5173/ws/dashboard`）→ 连通；
  `frame[1]` 15233 B 全量 `spot=765.58 snapshot_version=64658`；`frame[2]/[3]` 增量 248 B / 11763 B

W2 回归与实测：

- `PYTHONNOUSERSITE=1 ... -m pytest infra/ops_cli/ app/tests/test_start_backend_strict_restart.py -q` → **46 passed**
- `PYTHONNOUSERSITE=1 ... -m pytest infra/ app/ shared/ --ignore=app/tests/test_health_route_diagnostics.py` → **180 passed**
- 第 1 次启动 → `logs/2026-09-29/backend/run-001.log` 42690 B、`logs/2026-09-29/frontend/run-001.log`
- 第 2 次启动 → `run-002.log` 22270 B；`run-001` 首行仍为 `[2026-09-29 10:13:00] [BOOT] mode=strict ...`（未被覆盖）
- 第 3 次启动（WMI 脱离会话）→ `run-003.log`；跨命令增长 **16030 → 102110 B**
- 格式逐字一致（抽查）：`[2026-09-29 10:13:00] [BOOT] mode=strict host=0.0.0.0 port=8001`、
  `INFO:     Started server process [27368]`、
  `2026-09-29 10:16:21 [INFO] [L1ComputeReactor] compute n=120 tier=numpy t=31.0ms gex=-1687.46 ... rust_active=True shm_status=OK`
- 存活复查（本会话末）：`netstat` → `0.0.0.0:8001 LISTENING 27368`、`0.0.0.0:5173 LISTENING 24556`；
  `curl --noproxy '*'` → backend `200`、frontend `200`；run-003 里 `Started server process [27368]` 与监听 pid 一致
- 前端日志为空的归因（非空转式确认）：
  `VITE_BACKEND_ORIGIN=http://127.0.0.1:8001 timeout 12 node ./scripts/preview-strict.mjs --host 127.0.0.1 --port 5199 --strictPort > /tmp/fe_probe.log 2>&1`
  → `exit=124`（跑满 12 s 未退出）、输出 **0 字节** ⇒ 该脚本成功启动时本身零输出；
  失败时才写 stderr（`logs/frontend_runtime.current.log:440` 有 `error when starting preview server:`）

W1 收尾 —— 400 行门禁修复（`builder.py` 被我推到 401）：

- `wc -l` → `builder.py` **401 → 265**、`arrow_transport.py` **180**（均 < 400）
- `git show HEAD:.../builder.py | wc -l` → `399`（基线；+2 即我引入的违规）
- `python -c "import ...builder"` → `issubclass(OptionChainBuilder, ArrowTransportMixin) = True`，
  16 个方法/属性全部可解析（`missing attrs = []`），`_is_arrow_transient_error` 静态行为不变
- 逐个 import 符号 `grep -c` → 全部 ≥2（无残留未使用 import）
- `pytest scripts/test/test_l0_arrow_startup_gate.py shared/services/l0_runtime/services/runtime/ -q` → **8 passed**
  （该脚本直接调用被移出的 `_await_arrow_writer_ready_or_fail` / `_is_arrow_transient_error`，是切分的关键回归锚点）

W2 第 4 次启动（重构后重启，验证切分未破坏启动链路）：

- WMI 拉起 → `ReturnValue=0 ProcessId=25680`；约 25 s 后 `/health=200`
- `logs/2026-09-29/backend/run-004.log` 生成，首行 `[2026-09-29 10:27:44] [BOOT] mode=strict host=0.0.0.0 port=8001`
- `logs/2026-09-29/frontend/run-004.log` 生成（0 字节 = 健康）
- **前端日志并非永远为空**：`frontend/run-003.log` 记录了后端重启窗口内的
  `[vite] ws proxy error: connect ECONNREFUSED 127.0.0.1:8001`（10:27:38–10:28:05）⇒ 有输出时确实写入
- **跳过 Redis 不留空文件**：`ls logs/2026-09-29/` → 只有 `backend` / `frontend`，无 `redis` 目录

## VALIDATION-SUMMARY

- `pytest infra/ops_cli/ shared/.../test_bootstrap.py -q` → 40 passed（W1）
- `pytest infra/ops_cli/ app/tests/test_start_backend_strict_restart.py -q` → 46 passed（W2）
- `pytest infra/ app/ shared/ --ignore=...test_health_route_diagnostics.py -q` → 180 passed（W2 全量，重构后复跑）
- `pytest scripts/test/test_l0_arrow_startup_gate.py shared/.../runtime/ -q` → 8 passed（切分回归锚点）
- `manage.py check-layer-boundaries` → OK
- `manage.py start-all` 端到端 → 后端/前端/数据通路三项全绿（W1+W2+重构后各一次）
- 日志两维归档 → 当日 4 次启动产生 run-001..004，互不覆盖（W2）

## Closed in session

- **启动卡死根因（三层）**：网络触发 + 重试配置死接线 + readiness gate 盲等 → 已修，且给了非空转对照。
- **`start_all.py` 405 行超门禁** → 拆为 `start_all.py`(267) + `frontend_launch.py`，通用原语下沉 `common.py`。
- **`app/tests/test_start_backend_strict_restart.py` 既有红测** → 断言改为真实的 PowerShell 停止序列。
- **日志两维归档** → 落地 `logs/<date>/<service>/run-<NNN>.log`，三服务各自申领，跳过服务不留空文件。
- **「长驻服务无法从自动化会话启动」的旧结论** → 推翻；WMI `Win32_Process.Create` 有效（详见复盘「遗留」段）。
- **`main.py` 硬编码 DEBUG 这条遗留的措辞** → 核实为「HEAD 上成立、工作区已被他人在改」，复盘已改写。
- **`builder.py` 401 行门禁违规（我引入）** → 切出 `arrow_transport.py`，401 → 265，8 例脚本回归通过。
- **`longport_startup_strict_connectivity` 的 `getattr(..., True)` 静默兜底** → 本轮改为直接属性访问；
  复盘与 `notes/context/open_tasks.md` 中的旧措辞已同步纠正。
- **工作区清空并推送远端**（KAI 明确要求「提交远端，保持工作区干净」）。7 个提交推上
  `origin/codex/research-persistence-startup-fixes-20260423`：`.gitignore`、l0 探针修复 + Arrow 切片、
  日志归类、本会话记录、他会话的持久化改动（单独一个提交并注明非本会话作者）、冷数据归档。
  收尾时工作区 0 改动、`HEAD` == `origin/<branch>`、未推 0 个。

## NOTES-PATHS

- `notes/sessions/2026-09-29/startup-probe-fix-and-log-layout/handoff.md`
- `notes/sessions/2026-09-29/startup-probe-fix-and-log-layout/project_state.md`
- `notes/postmortem/2026-09-29-startup-probe-single-shot.md`
- `.workbuddy-ai/memory/2026-09-29.md`
- `C:\Users\Lenovo\.workbuddy-ai\skills\windows-detached-service-launch\SKILL.md`

## OPEN-RISKS

- **他会话的在途改动已按 KAI 明确授权提交**（本会话收尾阶段，见 `## Closed in session`），
  单独一个提交并注明「非本会话作者、未再验证」：`l3_assembly/reactor.py`、`l3_assembly/test_reactor.py`、
  `l4_ui/src/components/center/AtmDecayOverlay.tsx`、`main.py`、`shared/config/persistence.py`、
  `shared/services/l0_runtime/native_loader.py`、`shared/services/l0_runtime/durable_parquet_write.py`、
  `shared/services/l0_runtime/test_durable_parquet_write.py`，以及两份 9-24 / 9-25 复盘。
  **风险仍在**：这批代码本会话只做了字节编译检查，没跑回归。
- **本环境的 git 引用存储有缺陷**（`.git/refs` 下的二级子目录会被删），
  直接后果是嵌套分支名下第二次 `git commit` 会静默变成 **root commit**。
  本会话踩到并已恢复；处理手法已写进跨项目 skill `git-tracking-ref-stale`，
  **此处不重复**。下次在本仓提交前先读那个 skill。
- `data/cold/**` 与根目录三个临时产物（`.workbuddy-ai/`、`tmp_openapi.json`、`atm-decay-*.png`）
  已分别提交 / 加入 `.gitignore`，见提交历史。
- `[SubscriptionManager] Quote runtime connected.` 是误导性日志（`shared/services/l0_runtime/services/subscription/__init__.py:174-175`，
  `connect()` 无网络 I/O，探针失败时照样打印）。**未改，等裁定。**
- 端点可达性**仍无常驻检查器**（9-25 已记）。候选：把 `tmp/_probe_dashboard_ws.py` 固化进 `tools/`。**等裁定。**
- 前端 `run-*.log` 成功启动时为 0 字节 —— 经实测确认是该脚本本身零输出，**不是回归**；
  但「空文件」作为健康信号不直观，是否需要写一行启动标记**待裁定**。
- `app/tests/test_health_route_diagnostics.py` 依赖 `httpx`（环境未装），全量回归时被 `--ignore` 排除。

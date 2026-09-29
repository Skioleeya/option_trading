# Project State — startup-probe-fix-and-log-layout

## Scope Understanding

- **In scope**
  - W1：定位并修复 `manage.py start-all` 卡在 backend readiness gate 的根因。
  - W2：日志输出改为按「交易日 + 启动序号」两维自动归类，且不改变既有格式与内容。
  - 附带：触碰到的文件必须满足 400 行门禁与分层约束（`AGENTS.md` 硬门禁）。
- **Out of scope**
  - 不改端点配置、不改 mihomo / DNS / TUN（层 1 是环境侧触发条件，非本仓缺陷）。
  - 不动 L0→L1→L2→L3→L4 的任何业务语义与契约。
  - 不修他会话在工作区留下的未提交改动。

## 两个工作流为何放在同一 session root

同一会话内先后发生，且共享同一份「启动链路」上下文（W2 的日志申领点全部落在 W1 拆分后的
`start_all.py` / `frontend_launch.py` / `start_backend.py` 上）。拆成两个 root 会重复同一份路径清单。
二者的证据互不重叠，已在 `handoff.md` 内以 W1 / W2 分区标注。

## 设计取舍（W1）

### 为什么重试只覆盖传输异常

`_probe_quote_rows_with_retry` **只在抛异常时重试**；`runtime.quote()` 返回行集（哪怕空集）一律直接返回。
理由：空行集是**数据契约结果**，重试它等于把「订阅/契约坏了」掩盖成「网络慢」。
这条有专门的非空转对照 —— `test_startup_connectivity_probe_does_not_retry_data_contract_failures`
断言 `last_done=0` 时 `calls==1`。

### 为什么非法重试策略直接抛错

`_resolve_retry_policy` 对 `retries < 1` 与 `base < 0` 抛 `RuntimeError`，**不提供隐式默认**。
按 `AGENTS.md` 的 fail-fast：配置加载器不含业务默认值，缺键/非法值即抛错。
若这里兜底成 `attempts=1`，就等于把「配置写错」静默降级成「单次探测」—— 正是本次事故的形状。

### 为什么失败后重抛原始异常

不改写错误串，保持 `startup connectivity probe failed for quote runtime: profile=... endpoint=... error=...`
前缀不变，仅在末尾追加 `attempts=N`。理由：既有排查习惯是 grep 该前缀；换成新串会让历史 runbook 失效。

### 为什么不放宽 readiness gate 的超时

超时 180 s 不是缺陷，**盲等**才是。缺陷在 `_wait_backend_healthy` 不检查子进程是否已退出。
所以修的是「子进程已死 → 立即返回 False」，而不是「等更久」—— 后者属于补丁式绕过。

### 拒绝的方案

| 方案 | 拒绝理由 |
|---|---|
| 关闭 `strict_connectivity` 让后端照常启动 | 策略明确禁止（`strict_connectivity=false is forbidden by runtime policy`）；且会把「端点不可达」变成「起来了但没数据」 |
| 把 readiness 超时从 180 s 调大 | 治标；后端早已死亡，只是没人发现 |
| 在 `start_all.py` 内加 `if` 分支兼容旧的三条 `--*-log` 参数 | 兼容分支堆叠；旧参数无外部调用方，直接删除 |

## 设计取舍（W2）

### 为什么用「目录 + 文件」两层而不是单文件改名

- 日期层用**目录**：跨天归档只需按目录搬走，无需解析文件名。
- 服务层用**目录**：三个服务的序号各自独立（backend 的 run-003 与 frontend 的 run-003 无关系），
  放在同一目录会让 `run-NNN` 语义含混。
- 序号用**定宽 3 位**：`ls` 字典序即时间序，不需要 `sort -V`。

### 交易日而非自然日

日期用 `America/New_York` 的交易日（`TRADING_TIMEZONE`）。理由：本仓所有时间语义都绑 ET
（`_today_et_iso` 原本就是这个口径）。若用本地/UTC 日期，跨零点启动会分裂到两个目录，
与「一次交易日一个分组」的意图不符。有测试锁定：`2026-09-29 01:30 UTC` → `2026-09-28`。

### 序号申领为什么要排他创建

`allocate_run_log_path` 用 `open("x")` 排他创建占位，而不是「先扫最大值 +1 再交给子进程打开」。
理由：后者在并发/残留场景下会两个启动抢同一个 `run-NNN` 并互相截断。
占位后若真的被抢（`FileExistsError`）就继续试下一个，最多 1000 次。

### 为什么删掉了 `allocate_run_logs`（复数版）

第一版实现了一次性为三个服务都申领路径。实测发现：Redis 已在跑时会被跳过，
于是留下一个**永远 0 字节的 redis run 文件** —— 空文件会被误读成「服务起来了但没输出」。
改为**每个服务在真正要启动的那一刻才申领自己的槽位**。
这条是本会话踩到的坑，不是设计前就想清楚的。

### 前端日志为空是如实反映，不是回归

`preview-strict.mjs` 成功启动时**本身零输出**（实测 `timeout 12 node ... > /tmp/fe_probe.log` → 0 字节）。
失败时才写 stderr。所以「空的 frontend run 日志」= 启动正常，非空 = 出问题。
`notes/sessions/2026-04-23/start-all-health-check/handoff.md:42` 已记录过同一现象，属既有已知缺口。

## 400 行门禁事故：我自己把 builder.py 推过了线

`HEAD:builder.py` 是 **399** 行。我把探针调用从 1 行 `getattr(...)` 改成 3 行显式 kwargs，
净 +2 ⇒ **401**，直接触发 `modularity-core` 的 P0（`AGENTS.md` 明列 `exceed 400 lines` 为 hard-stop）。

**处理原则**：不接受「再砍 1 行凑到 400」。400 是天花板而不是目标，
靠删一行空行过关属于补丁式绕过，下一次任何人加一行就再破一次。
所以做真实切分。

### 切什么

`builder.py` 实际承担两件事：**L0 门面编排** 与 **Arrow IPC 传输适配**。
后者（reader 生命周期 / 批量消费 / 瞬时错误恢复 / 传输状态载荷）自成一类，约 110 行。

### 为什么用 mixin

- 仓库现有惯用法是**模块级函数 + 显式协作者**（`arrow_events.py::handle_arrow_event` 即是）。
  但那些方法重度依赖 `self._arrow_reader / _transport_status / _services / _state / _hooks` 等
  十余个实例属性；改成模块级函数会退化成十来个 kwargs 或回调汤，**可读性净下降**。
- 改成独立类 + 组合（`self._transport = ArrowTransport(...)`）会**打断既有调用点**：
  `scripts/test/test_l0_arrow_startup_gate.py:62` 直接调
  `builder._await_arrow_writer_ready_or_fail(...)`，还断言 `OptionChainBuilder._is_arrow_transient_error(...)`。
  该脚本不在常规 pytest 范围（`infra/ app/ shared/`）内，破坏它不会被回归发现 —— 属于**静默破坏**。
- mixin 保持 `self` 是同一个对象，**所有调用点逐字不变**，`hasattr` 校验 16 个成员全部解析。

### 已知代价

仓库此前**没有 mixin 先例**，本文件引入了新惯用法。
属性声明块（`_runtime_bundle: Any` 等 14 行）是为让类型检查器看懂宿主类契约，属必要成本。
若后续 KAI 认为应统一改成别的切法，`arrow_transport.py` 是自足的，迁移成本低。

## 遗留的坑（给下一个会话）

- `notes/context/*` 用的是**已废除的旧形态**（`meta.yaml` + session 级 `open_tasks.md`），
  本会话已按新形态重写。旧 session root 一律不回溯改造。
- 工作区混入他会话未提交改动（见 `handoff.md::OPEN-RISKS`）。本会话刻意不纳入、不评价。
- `win32` 下 `.venv\Scripts\python.exe` 是 stub，真解释器是它的子进程 ——
  排查端口占用时看到两个 `python.exe` 属正常，**监听端口的是子进程**。

# Project State

## Snapshot
- DateTime (ET): 2026-04-20 10:37:32 -04:00
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `c61f06c`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DEGRADED` (Arrow IPC decode truncation observed)
  - L0-L4 Pipeline: `PARTIAL` (version and source timestamp stalled, frontend frozen)

## Current Focus
- Primary Goal: 修复前端全 UI 数据卡住（不仅 SPY）的根因，恢复版本推进与连续广播。
- Scope In:
  - `l0_ingest/l0_rust/src/ipc_legacy.rs` Arrow IPC 长度前缀发布协议修复。
  - `shared/services/l0_runtime/source/runtime/ipc.py` 解码坏帧分类与显式错误语义。
  - `shared/services/l0_runtime/services/runtime/builder.py` 可恢复坏帧重连状态机。
  - 回归测试与 SOP 同步。
- Scope Out:
  - 不做自动重启/自愈策略（仅根因修复）。
  - 不改前端渲染组件与 L2/L3 业务策略。

## What Changed (Latest Session)
- Files:
  - `l0_ingest/l0_rust/src/ipc_legacy.rs`
  - `shared/services/l0_runtime/source/runtime/ipc.py`
  - `shared/services/l0_runtime/services/runtime/builder.py`
  - `scripts/test/test_l0_arrow_startup_gate.py`
  - `docs/SOP/L0_DATA_FEED.md`
- Behavior:
  - Windows Arrow IPC 写入改为 `len=0 -> payload -> len=payload_len`，防止读侧拿到半包。
  - 读侧新增长度二次确认，不一致帧返回空 payload（由上层重试）。
  - Builder 将 `payload_empty/decode_failed/no_batch` 归类为 transient，执行受控重连并保持消费循环存活。
  - diagnostics 新增 `decode_failures_total`/`decode_failures_streak`。

## Verification
- `.venv/bin/python manage.py run-pytest scripts/test/test_l0_arrow_startup_gate.py` -> 5 passed
- `.venv/bin/python manage.py run-pytest scripts/test/test_active_options_freeze_rootcause.py` -> 3 passed
- `cargo check` (in `l0_ingest/l0_rust`) -> passed
- `python3 manage.py validate-session --strict` -> PASS（后续将用更新后的 files_changed 再跑一次）

## Risks / Constraints
- 仍需在真实主机盘前/盘中复核 WebSocket version 连续推进（sandbox 无法作为实盘证据）。
- OpenSpec 本次走紧急修复豁免，需后续治理会话补链路记录。

## Next Action
- Immediate Next Step: 更新 session/context 元数据并重跑 strict gate，随后提交本次变更。
- Owner: Codex

# Project State

## Snapshot
- DateTime (ET): 2026-03-19 10:30:31 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `d64eb98`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: 诊断 `l4_ui/src/components/right/ActiveOptions.tsx` 无真实数据（全占位）原因，并交付独立诊断脚本。
- Scope In:
  - 日志证据链梳理（`ActiveOptionsRuntimeService`、Spot fallback、token 连接失败）
  - 新增独立脚本：`scripts/diag/check_active_options_no_data_cause.py`
  - 会话记录更新（session-local）
- Scope Out:
  - 运行时业务逻辑改造（L0/L1/L2/L3/L4）
  - 前端 UI 行为修改

## What Changed (Latest Session)
- Files:
  - `scripts/diag/check_active_options_no_data_cause.py`
  - `notes/sessions/2026-03-19/diagnose-active-options-empty-20260319/project_state.md`
  - `notes/sessions/2026-03-19/diagnose-active-options-empty-20260319/open_tasks.md`
  - `notes/sessions/2026-03-19/diagnose-active-options-empty-20260319/handoff.md`
  - `notes/sessions/2026-03-19/diagnose-active-options-empty-20260319/meta.yaml`
- Behavior:
  - 新脚本可独立输出 ActiveOptions 无数据诊断结论，综合日志 + `/debug/persistence_status` + `/history`（接口可用时）进行证据判定。
  - 接口不可达时自动降级到日志证据，不静默失败。
- Verification:
  - `python scripts/diag/check_active_options_no_data_cause.py`
  - `python scripts/diag/check_active_options_no_data_cause.py --json`
  - `python -m py_compile scripts/diag/check_active_options_no_data_cause.py`
  - `./scripts/validate_session.ps1 -Strict`

## Risks / Constraints
- Risk 1: 当前环境出现 `WinError 10106`，诊断脚本无法从本 shell 访问本机 `127.0.0.1:8001`，HTTP 证据路径受限。
- Risk 2: 日志显示 `Spot REST fallback failed` 与 `socket/token` 失败，实时成交量字段可能不足，导致 `min_volume` 过滤后全空。

## Next Action
- Immediate Next Step: 在用户本机 PowerShell 执行诊断脚本并根据输出先恢复行情连通性，再验证 `FLOW_ACTIVE_MIN_VOLUME` 阈值。
- Owner: Codex

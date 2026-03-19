# Project State

## Snapshot
- DateTime (ET): 2026-03-19 11:16:59 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `d64eb98`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: 修复前台启动 NativeCommandError 与 ActiveOptions 长期全占位（real=0）问题。
- Scope In:
  - `scripts/ops/start_backend.ps1` 前台启动路径切换到 `cmd /c` 包裹 uvicorn。
  - `shared/services/active_options/runtime_service_support.py` 增强字段别名归一化。
  - `shared/services/active_options/runtime_service_support.py` 在 `chain` 非空且无 `turnover/open_interest` 候选时启用硬回退候选。
  - `shared/services/active_options/runtime_service.py` 区分回退日志模式（普通 fallback / hard fallback）。
  - `shared/services/active_options/test_runtime_service.py` 增补别名与硬回退回归测试。
- Scope Out:
  - L2/L3/L4 合同调整。
  - 行情连通性根因修复（`socket/token` 网络问题）。

## What Changed (Latest Session)
- Files:
  - `scripts/ops/start_backend.ps1`
  - `shared/services/active_options/runtime_service.py`
  - `shared/services/active_options/runtime_service_support.py`
  - `shared/services/active_options/test_runtime_service.py`
  - `notes/sessions/2026-03-19/fix-start-backend-active-options-fallback-20260319/open_tasks.md`
- Behavior:
  - 前台启动不再直接用 PowerShell `& python`，改为 `cmd.exe /c` 执行 uvicorn，避免 stderr 日志触发 `NativeCommandError`。
  - ActiveOptions 在 min-volume 过滤为空时，先做字段别名归一化（`amount/openInterest/currentVolume/strike_price/last_done/iv/hv` 等）。
  - 若 `turnover/open_interest` 也不可用但 `chain` 非空，启用硬回退并注入最小可计算 `volume`，保证可产出真实行。
- Verification:
  - `./scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py -q` (18 passed)
  - `./scripts/ops/start_backend.ps1 -Foreground -HotfixActiveOptions -HotfixMinVolume 10 -DryRun`
  - `./scripts/validate_session.ps1 -Strict` (pass)

## Risks / Constraints
- Risk 1: 主机网络栈异常（`WinError 10106` / `socket/token`）仍可能导致真实行情稀疏，影响在线验活稳定性。
- Risk 2: 本轮通过硬回退确保“非全占位”连续性，但信号质量仍依赖上游实时成交字段密度。

## Next Action
- Immediate Next Step: 在用户终端执行前台热修启动并运行 `scripts/ops/verify_active_options_hotfix.ps1`，确认 `chain_size>0` 时 `real>=1`。
- Owner: User/Codex

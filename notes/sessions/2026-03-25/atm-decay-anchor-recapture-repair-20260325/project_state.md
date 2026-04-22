# Project State

## Snapshot
- DateTime (ET): 2026-03-25 10:55:14 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `70cc81b`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: 修复 ATM decay 坏锚点不会自愈的问题，并清除 2026-03-25 当日锚点让系统重新判定新的 ATM。
- Scope In: `l1_compute.analysis.atm_decay` 失效/重锁逻辑、`app/loops/housekeeping_loop.py` mandatory symbol 同步、相关测试、OpenSpec/SOP/session 同步、当日 anchor/history 清理与 backend 重启。
- Scope Out: L3/L4 合同改版、ATM decay 数学改写、TradingView 视觉重构。

## What Changed (Latest Session)
- Files: `l1_compute/analysis/atm_decay/{models,storage,tracker,runtime}.py`、`app/loops/housekeeping_loop.py`、`app/loops/tests/test_housekeeping_gpu_dedup.py`、`l1_compute/tests/test_atm_decay_anchor_recovery.py`、`docs/SOP/L1_LOCAL_COMPUTATION.md`、`openspec/changes/refactor-dependency-20260325-atm-decay-anchor-recapture-repair/*`
- Behavior: ATM tracker 在连续 `raw_pct_unavailable` 达阈值后会自动 invalidation 并清除 persisted same-day anchor；housekeeping 会在 anchor 清空时显式同步空 mandatory set。已清除当日旧 anchor/history 并重启 backend，系统重新锁定了新的 662 strike anchor。
- Verification: 新增回归测试通过；既有 tracker/housekeeping 回归通过；当日 `atm_20260325.json` 已由旧 `657` 锚点切换为新 `662` 锚点；`scripts/validate_session.ps1 -Strict` 已通过。

## Risks / Constraints
- Risk 1: 当前在线验证仍未观察到新锚点后的首个有效 decay history 点；`/api/atm-decay/history` 仍为 `count=0`，说明新锚点已重锁但首个有效两腿价格尚未形成或仍在等待修复。
- Risk 2: 工作区存在大量本任务之外的未提交变更，必须避免误回滚。

## Next Action
- Immediate Next Step: 继续盘中观察新锚点后的首个有效 decay history 点，并在形成后核对 `/api/atm-decay/history` 与 `/ws/dashboard` 是否同步恢复。
- Owner: Codex

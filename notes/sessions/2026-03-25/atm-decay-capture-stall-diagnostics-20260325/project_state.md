# Project State

## Snapshot
- DateTime (ET): 2026-03-25 11:57:09 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `70cc81b`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: 为 ATM fresh-capture stall 增加足够强的 L1 取证日志，便于继续定位首个 post-lock decay 点未落入 history/API 的原因。
- Scope In: `l1_compute.analysis.atm_decay.{anchor,models,runtime,tracker}`、L1 回归测试、SOP/OpenSpec/session 文档。
- Scope Out: LongPort SDK 网络层重试、ATM decay 数学公式、前端 chart 行为、storage/API 合同改版。

## What Changed (Latest Session)
- Files: `l1_compute/analysis/atm_decay/models.py`、`l1_compute/analysis/atm_decay/anchor.py`、`l1_compute/analysis/atm_decay/runtime.py`、`l1_compute/analysis/atm_decay/tracker.py`、`l1_compute/tests/test_atm_decay_tracker.py`、`docs/SOP/L1_LOCAL_COMPUTATION.md`、`openspec/changes/refactor-dependency-20260325-atm-decay-capture-stall-diagnostics/*`
- Behavior: fresh-capture 失败现在会累计 `_capture_failure_streak`，并在阈值倍数时输出 INFO 级 `capture stall` forensic log；`No 0DTE contracts` 也提升为 INFO。成功锁锚、invalidate、新交易日 reset 都会清零该 streak。
- Verification: `l1_compute/tests/test_atm_decay_tracker.py` 与 `l1_compute/tests/test_atm_decay_modular.py` 已通过；`scripts/validate_session.ps1 -Strict` 已通过。

## Risks / Constraints
- Risk 1: 当前 runtime 主问题仍未闭环，`/api/atm-decay/history` 的首个 post-lock 样本尚未出现；本 session 只增强 observability，不直接修复成因。
- Risk 2: 工作区存在大量本任务之外的未提交改动和新增文件，必须避免误回滚。

## Next Action
- Immediate Next Step: 继续在线观察新的 `capture stall` forensic log，定位首个 post-lock ATM decay 样本未进入 history/API 的真实卡点。
- Owner: Codex

# Project State

## Snapshot
- DateTime (ET): 2026-03-09 15:19:46 -04:00
- Branch: master
- Last Commit: f2268d2
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 修复后端重启时 startup spot 不可用导致 ATM 锚点不恢复、盘中图表重新开锚的问题。
- Scope In:
  - `AtmDecayTracker` 增加 deferred-restore（延迟恢复）机制。
  - 新增回归测试覆盖“spot unavailable -> later restore”。
  - SOP 同步更新恢复策略。
- Scope Out:
  - 不改 L3/L4 payload 契约与前端组件逻辑。

## What Changed (Latest Session)
- Files:
  - l1_compute/analysis/atm_decay/tracker.py
  - l1_compute/tests/test_atm_decay_modular.py
  - docs/SOP/L1_LOCAL_COMPUTATION.md
- Behavior:
  - 启动阶段若 `spot` 不可用，不直接丢弃持久化 anchor，而是进入 deferred 状态；
    在后续 tick 收到有效 spot 时再执行严格距离校验并恢复，避免盘中新开锚。
- Verification:
  - `scripts/test/run_pytest.ps1 l1_compute/tests/test_atm_decay_modular.py l1_compute/tests/test_wall_migration_tracker.py` 通过（12 passed）。

## Risks / Constraints
- Risk 1: 未执行全量后端回归，仅执行目标链路定向回归。
- Risk 2: 若运行环境长期无有效 spot，仍会保持待恢复状态直到可校验。

## Next Action
- Immediate Next Step: 运行 strict gate 并现场复测“重启后 anchor 不新开”。
- Owner: Codex/User

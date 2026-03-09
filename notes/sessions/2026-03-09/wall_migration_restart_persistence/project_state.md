# Project State

## Snapshot
- DateTime (ET): 2026-03-09 15:04:36 -04:00
- Branch: master
- Last Commit: f2268d2
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 为 WallMigration 增加后端冷存储恢复，确保后端闪崩重启后盘中历史窗口连续。
- Scope In:
  - L1 新增 wall migration JSONL 持久化模块（按交易日）。
  - WallMigrationTracker 增加懒加载恢复 + 追加持久化（失败显式降级）。
  - `shared.config` 增加 `wall_migration_cold_storage_root`。
  - 增补 L1 测试与 SOP 文档同步。
- Scope Out:
  - 不改 L4 组件 (`WallMigration.tsx`, `AtmDecayChart.tsx`) 业务逻辑。
  - 不新增前端 API 或 payload 字段。

## What Changed (Latest Session)
- Files:
  - shared/config/persistence.py
  - l1_compute/trackers/wall_migration_storage.py
  - l1_compute/trackers/wall_migration_tracker.py
  - l1_compute/tests/test_wall_migration_tracker.py
  - docs/SOP/L1_LOCAL_COMPUTATION.md
- Behavior:
  - WallMigration 支持按交易日 JSONL 冷存储恢复（`data/wall_migration/wall_series_YYYYMMDD.jsonl`）。
  - Tracker 首次 tick / 交易日切换时懒加载最近窗口；每次有效快照 append 持久化。
  - 持久化失败显式日志，不中断 L1 计算与下游广播链路。
- Verification:
  - `scripts/test/run_pytest.ps1 l1_compute/tests/test_wall_migration_tracker.py l1_compute/tests/test_atm_decay_modular.py` 通过（11 passed）。

## Risks / Constraints
- Risk 1: 未执行全量后端回归，仅执行目标模块与 ATM 持久化回归。
- Risk 2: 生产环境磁盘权限或路径异常会触发降级日志，需运行期观察。

## Next Action
- Immediate Next Step: 运行 strict gate 并在实盘/仿真观察 wall history 重启恢复连续性。
- Owner: Codex/User

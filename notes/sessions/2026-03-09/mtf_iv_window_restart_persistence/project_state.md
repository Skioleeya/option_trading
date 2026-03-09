# Project State

## Snapshot
- DateTime (ET): 2026-03-09 16:21:02 -04:00
- Branch: master
- Last Commit: f2268d2
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 为 L1 `MTFIVEngine` 增加交易日内窗口冷存储与重启恢复，避免后端闪崩导致长时间暖机失真。
- Scope In:
  - 新增 MTF 窗口存储模块与持久化协调模块。
  - `MTFIVEngine` 增加纯状态导入导出接口（不做 I/O）。
  - `L1ComputeReactor` 接入 persistence 协调器（编排层）。
  - 增加持久化单测并更新 L1 SOP。
- Scope Out:
  - 不改 L3/L4 payload 结构。
  - 不改前端组件，不做事件全量回放。

## What Changed (Latest Session)
- Files:
  - l1_compute/analysis/mtf_iv_engine.py
  - l1_compute/trackers/mtf_iv_window_storage.py
  - l1_compute/trackers/mtf_iv_persistence.py
  - l1_compute/reactor.py
  - l1_compute/tests/test_mtf_iv_persistence.py
  - shared/config/persistence.py
  - docs/SOP/L1_LOCAL_COMPUTATION.md
- Behavior:
  - MTF 窗口支持按交易日 JSONL 冷存储并在重启后恢复最近快照。
  - 跨日自动 reset，不串历史；写盘失败仅日志降级，不阻断 compute。
  - Reactor 每 tick 最多一次窗口快照写入（仅当窗口更新）。
- Verification:
  - 新增持久化测试通过；reactor 与 wall_migration 回归通过。

## Risks / Constraints
- Risk 1: 持久化仅恢复窗口快照，不恢复 in-flight `_mtf_buf/_mtf_last_push`，重启后采样节奏短暂重建。
- Risk 2: 运行测试会生成 `data/mtf_iv` 运行期产物，需要按 runtime artifact 处理。

## Next Action
- Immediate Next Step: 运行 strict gate：`scripts/validate_session.ps1 -Strict`。
- Owner: Codex/User

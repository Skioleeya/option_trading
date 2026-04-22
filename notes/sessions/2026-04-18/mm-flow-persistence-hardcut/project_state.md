# Project State

## Snapshot
- DateTime (ET): 2026-04-18 07:58:46 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `c114661`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED` (offline/test validation session)
  - L0-L4 Pipeline: `DEGRADED` (no live broker startup in this fix session)

## Current Focus
- Primary Goal: Fix MM FLOW persistence断点，保证 feature parquet 持久化包含完整 9 字段（无 fallback）。
- Scope In: `shared_rust_services` 写盘路径、schema/allowlist 同步、`l0_rust` schema spec、SOP 与回归测试。
- Scope Out: 历史全量回填（缺少原始源数据）、compact 视图扩展、L2/L3 合同改造。

## What Changed (Latest Session)
- Files: `research_store.rs`、`research_schema.rs`、`research_store_support.rs`、`service_support.rs`、新增 `test_research_store_mm_flow_persistence.py`、更新 `docs/SOP/L3_OUTPUT_ASSEMBLY.md`。
- Behavior: `append_tick` 现在强制从 `payload.fused_signal.mm_flow` 读取并写入 9 个 MM FLOW 字段；缺失/非数值/非有限值即抛错，禁止静默降级。
- Verification: MM FLOW 合同测试 + 新持久化测试通过；`validate_session.ps1 -Strict` 已通过。

## Risks / Constraints
- Risk 1: 历史 `feature_*.parquet` 无 MM FLOW 列，无法在“无 fallback”前提下进行历史重算回填。
- Risk 2: 本次为前向修复；历史补齐依赖补采原始源数据。

## Next Action
- Immediate Next Step: 归档会话并等待原始源数据后执行历史回填会话。
- Owner: Codex

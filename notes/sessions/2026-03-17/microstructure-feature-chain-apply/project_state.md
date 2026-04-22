# Project State

## Snapshot
- DateTime (ET): 2026-03-17 12:20:45 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `cbccdaa`
- Environment:
  - Market: `UNKNOWN`
  - Data Feed: `DEGRADED` (pytest runtime env issue)
  - L0-L4 Pipeline: `OK` (strict quality/openspec gates green)

## Current Focus
- Primary Goal: 落地 OpenSpec `l0-l2-microstructure-feature-chain-repair` 的 runtime 修复与最小回归。
- Scope In:
  - `l0_ingest/feeds/option_chain_builder.py`
  - `l0_ingest/feeds/chain_state_store.py`
  - `l2_decision/feature_store/extractors.py`
  - 对应单测 + OpenSpec `tasks.md`
- Scope Out:
  - 不改 L3/L4 行为语义
  - 不做广义重构

## What Changed (Latest Session)
- Files:
  - Runtime:
    - `l0_ingest/feeds/option_chain_builder.py`
    - `l0_ingest/feeds/chain_state_store.py`
    - `l2_decision/feature_store/extractors.py`
  - Tests:
    - `l0_ingest/tests/test_chain_state_store.py`
    - `l0_ingest/tests/test_option_chain_builder_rust_events.py`
    - `l2_decision/tests/test_feature_store.py`
    - `l2_decision/tests/test_institutional_logic.py`
  - Spec Tracking:
    - `openspec/changes/l0-l2-microstructure-feature-chain-repair/tasks.md`
- Behavior:
  - Rust SHM 事件链路新增 depth/trade 回调桥接，回调异常显式日志且不阻断主循环。
  - Store 引入 WS 字段所有权标记，REST 仅在 WS 未见字段时兜底 `volume/current_volume/turnover`。
  - `turnover_velocity` 支持 `turnover -> current_volume -> volume` 口径回退。
  - `peak_impact` 支持 `RecordBatch`，并优先使用 `computed_gamma`。
- Verification:
  - `python -m py_compile ...` -> PASS
  - `./scripts/validate_session.ps1 -Strict` -> PASS
  - `./scripts/test/run_pytest.ps1 ...` -> BLOCKED (WinError 10106)

## Risks / Constraints
- Risk 1: 本机 Python/asyncio Windows provider 异常（`_overlapped` 导入失败）导致 pytest 采集失败。
- Risk 2: 在未修复环境前，无法完成 DoD 中的完整回归证明。

## Next Action
- Immediate Next Step: 修复/切换可用 Python 运行环境后重跑 pytest，并补齐 OpenSpec 验证子项。
- Owner: Codex

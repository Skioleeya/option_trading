# Project State

## Snapshot
- DateTime (ET): 2026-04-03 09:30:54 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `aa3efd7`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: 并行完成 Wave1 两个 L1 bridge marshalling 审计执行：`streaming_aggregator` 与 `greeks_engine`。
- Scope In:
  - `l1_compute/aggregation/streaming_aggregator.py`
  - `shared_rust_services/src/aggregation.rs`
  - `l1_compute/tests/test_streaming_aggregator_rust_parity.py`
  - `l1_compute/analysis/greeks_engine.py`
  - `shared/services/greeks_engine_batch.py`
  - `l1_compute/tests/test_greeks_engine_bridge.py`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `openspec/changes/impl-20260403-l1-streaming-aggregator-bridge-marshalling-audit/*`
  - `openspec/changes/impl-20260403-l1-greeks-engine-bridge-marshalling-audit/*`
- Scope Out:
  - 无关 L2/L3/L4 运行时代码与业务逻辑变更

## What Changed (Latest Session)
- Files:
  - `l1_compute/aggregation/streaming_aggregator.py`
  - `shared_rust_services/src/aggregation.rs`
  - `l1_compute/tests/test_streaming_aggregator_rust_parity.py`
  - `l1_compute/analysis/greeks_engine.py`
  - `shared/services/greeks_engine_batch.py`
  - `l1_compute/tests/test_greeks_engine_bridge.py`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `openspec/changes/impl-20260403-l1-streaming-aggregator-bridge-marshalling-audit/*`
  - `openspec/changes/impl-20260403-l1-greeks-engine-bridge-marshalling-audit/*`
- Behavior:
  - `StreamingAggregator.full_recompute()` 删除 `np.asarray(...)` 冗余桥接；`_recompute_walls()` 改为 native sequence 直传 Rust `select_walls`。
  - `StreamingAggregator` 移除 Python `_find_flip_level()` owner；`flip_level_cumulative/flip_level` 由 Rust `aggregate_greeks_full` 返回。
  - `GreeksEngine.enrich()` 不再调用 `bsm_fast.compute_greeks_batch()`，改为经 `shared.services.greeks_engine_batch.build_greeks_batch_sync` 进入 Rust owner。
  - 新增 `shared/services/greeks_engine_batch.py` 中立 marshalling 服务，Rust owner 失败即显式抛错，无 fallback/兼容分支。
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_streaming_aggregator_rust_parity.py` -> PASS (3 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_greeks_engine_bridge.py` -> PASS (2 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l1_compute/tests/test_bsm_rust_parity.py` -> PASS (53 passed)
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> PASS

## Risks / Constraints
- Risk 1: 当前仓库存在与本任务无关的历史脏文件，未做回滚处理。
- Risk 2: 无本次 Wave1 交付阻塞。

## Next Action
- Immediate Next Step: Handoff complete.
- Owner: Codex

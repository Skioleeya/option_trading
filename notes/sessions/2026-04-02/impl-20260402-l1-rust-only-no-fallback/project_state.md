# Project State

## Snapshot
- DateTime (ET): 2026-04-02 16:53:03 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `65dbc0f`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 强制切换 L1 相关路径为 Rust-only，禁止 Python fallback 回归。
- Scope In:
  - `l1_compute/analysis/bsm_rust_bridge.py`、`bsm_fast.py`
  - `l1_compute/compute/gpu_greeks_kernel.py`
  - `l1_compute/aggregation/rust_bridge.py`、`streaming_aggregator.py`
  - parity tests 与 SOP/OpenSpec/会话文档
- Scope Out:
  - 新增 L2/L3/L4 行为
  - 新 Rust 算法模型扩展（仅切执行策略）

## What Changed (Latest Session)
- Files:
  - `l1_compute/analysis/bsm_rust_bridge.py`
  - `l1_compute/analysis/bsm_fast.py`
  - `l1_compute/compute/gpu_greeks_kernel.py`
  - `l1_compute/aggregation/rust_bridge.py`
  - `l1_compute/aggregation/streaming_aggregator.py`
  - `l1_compute/tests/test_bsm_rust_parity.py`
  - `l1_compute/tests/test_streaming_aggregator_rust_parity.py`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `openspec/changes/impl-20260402-l1-bsm-numpy-rust-fallback/tasks.md`
  - `openspec/changes/impl-20260402-l1-streaming-aggregator-rust/tasks.md`
  - `notes/sessions/2026-04-02/impl-20260402-l1-rust-only-no-fallback/*`
- Behavior:
  - Rust bridge 不再返回 `None`；Rust owner 不可用或执行失败时显式抛 `RuntimeError`。
  - `bsm_fast` Tier-3 不再回退 Python NumPy。
  - `GPUGreeksKernel` CPU path 不再回退 Python BSM math。
  - `StreamingAggregator` 聚合与墙位选择不再回退 Python。
- Verification:
  - `scripts/test/run_pytest.ps1 l1_compute/tests/` -> `56 passed`
  - `scripts/policy/check_layer_boundaries.ps1` -> PASS
  - AST parse check -> PASS

## Risks / Constraints
- Risk 1: `tmp/pytest_cache` 仍有 `nodeids` 写 warning（不影响测试通过）。
- Risk 2: none（strict gate 已复跑并通过）。

## Next Action
- Immediate Next Step: 进入下一执行波次（当前 session 已完成 strict 终验）。
- Owner: Codex

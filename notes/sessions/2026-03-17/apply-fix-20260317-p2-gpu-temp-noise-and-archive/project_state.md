# Project State

## Snapshot
- DateTime (ET): 2026-03-17 15:38:45 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `06be8f2`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED` (GPU-only blocked on host WinError 5)

## Current Focus
- Primary Goal: enforce GPU-only recomputation (禁止 CPU 重算) and complete `/opsx-archive` for completed P2 proposal.
- Scope In:
  - `l1_compute` compute routing and GPU fallback policy
  - benchmark noise reduction evidence
  - OpenSpec archive command and session closure docs
- Scope Out:
  - 未完成的其他子提案测试闭环（feature-extractors / option-chain-builder / boundary）不在本会话补做

## What Changed (Latest Session)
- Files:
  - `l1_compute/compute/gpu_greeks_kernel.py`
  - `l1_compute/compute/compute_router.py`
  - `l1_compute/output/enriched_snapshot.py`
  - `l1_compute/tests/test_compute.py`
  - `l1_compute/tests/test_reactor.py`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `openspec/changes/archive/2026-03-17-refactor-bloat-20260317-l0-l1-arrow-zero-copy-path/*`
  - `openspec/specs/bloat/spec.md`
- Behavior:
  - 默认策略改为 GPU-only：GPU 不可用或 GPU 运行失败时，禁止 CPU（Numba/NumPy）重算。
  - 路由显式输出 `compute_tier=gpu_only_blocked`，并返回阻断矩阵以维持链路连续。
  - benchmark 告警从每 tick 反复刷屏降为首条告警。
- Verification:
  - `scripts/test/run_pytest.ps1 l1_compute/tests/test_compute.py` -> 17 passed
  - `scripts/test/run_pytest.ps1 l1_compute/tests/test_reactor.py` -> 26 passed
  - `scripts/diagnostics/measure_l0_l1_conversion.py` -> PASS，L1 转换调用/耗时继续 100% 下降

## Risks / Constraints
- Risk 1: 当前主机 GPU 路径仍报 `WinError 5`，GPU-only 下会进入 blocked 降级模式。
- Risk 2: 其余 2026-03-17 提案尚未全部达到 `✓ Complete`，本次仅归档已完成的 P2 子提案。

## Next Action
- Immediate Next Step: 运行 strict gate 并同步 session/context/handoff 收口；后续若需继续 archive，先补齐未完成提案任务。
- Owner: Codex


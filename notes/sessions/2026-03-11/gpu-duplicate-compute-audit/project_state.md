# Project State

## Snapshot
- DateTime (ET): 2026-03-11 09:21:01 -04:00
- Branch: master
- Last Commit: fc174d4
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: GPU 重复计算与算力浪费专项审计，并完成 P0/P1 级修复。
- Scope In:
  - 审计 L0/L1/L2/L3 链路中同输入重复算、重复提交、无效拷贝路径。
  - 为 compute 路径补充 `tick_id/snapshot_version/compute_id/gpu_task_id` 证据。
  - 修复至少 P0/P1 并通过回归与 strict gate。
- Scope Out:
  - 不调整对外 API 结构（仅加兼容可选参数）。
  - 不改动交易策略语义与 UI 合同字段含义。

## What Changed (Latest Session)
- Files:
  - app/loops/compute_loop.py
  - app/loops/housekeeping_loop.py
  - app/loops/shared_state.py
  - l0_ingest/feeds/option_chain_builder.py
  - l1_compute/reactor.py
  - l1_compute/tests/test_reactor.py
  - app/loops/tests/test_compute_loop_gpu_dedup.py
  - app/loops/tests/test_housekeeping_gpu_dedup.py
  - docs/SOP/L0_DATA_FEED.md
  - docs/SOP/L1_LOCAL_COMPUTATION.md
- Behavior:
  - `compute_loop` 对同 `snapshot_version` 执行去重，重复 tick 不再触发 L1/L2/L3 计算。
  - `fetch_chain` 默认关闭 legacy Greeks 重算，保留 `include_legacy_greeks` 兼容开关。
  - `housekeeping_loop` 复用最新 L1 快照并按版本去重，避免重复上游请求与重复提交。
  - L1 计算链输出 `computed_gamma/computed_vanna` 并记录 GPU 审计日志。
- Verification:
  - `scripts/test/run_pytest.ps1 app/loops/tests/test_compute_loop_helpers.py app/loops/tests/test_compute_loop_gpu_dedup.py app/loops/tests/test_housekeeping_gpu_dedup.py l1_compute/tests/test_reactor.py` 通过（28 passed）。

## Risks / Constraints
- Risk 1: ActiveOptions 在首次 L1 快照到达前仍走 fallback 空链路径，可能短暂显示占位。
- Risk 2: legacy Greeks 兼容开关若被外部频繁启用，仍可能引入额外算力占用。

## Next Action
- Immediate Next Step: 执行 strict gate，完成会话 handoff 与债务记录闭环。
- Owner: Codex

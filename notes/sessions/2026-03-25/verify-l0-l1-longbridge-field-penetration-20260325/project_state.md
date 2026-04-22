# Project State

## Snapshot
- DateTime (ET): 2026-03-25 22:51:11 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `2b286ae`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK (targeted offline verification)`
  - L0-L4 Pipeline: `OK (targeted tests)`

## Current Focus
- Primary Goal: 验证纯 Rust L0 到 L1 的 LongPort/Longbridge 关键字段穿透，并补可见的数据流诊断日志，让 GEX、vanna、charm、S-VOL 和 Active Options flow 都有明确观测点。
- Scope In:
  - `l1_compute/reactor.py` L0->L1 ingress / L1 compute summary logs
  - `shared/services/active_options/input_adapter.py` L1 计算字段覆盖日志
  - `app/loops/housekeeping_loop.py` Active Options flow 输出日志
  - 相关 targeted pytest 与 session/context 同步
- Scope Out:
  - 新的跨层合同修改
  - 实盘会话长时间验活
  - 与本次诊断无关的 ATM / frontend backlog

## What Changed (Latest Session)
- Files:
  - `l1_compute/reactor.py`
  - `l1_compute/reactor_support.py`
  - `l1_compute/tests/test_reactor.py`
  - `shared/services/active_options/input_adapter.py`
  - `shared/services/active_options/test_input_adapter.py`
  - `app/loops/housekeeping_loop.py`
  - `app/loops/tests/test_housekeeping_gpu_dedup.py`
- Behavior:
  - `L1ComputeReactor` 现在在同一条 compute 路径里显式记录 `rust_active/shm_status/source_data_timestamp_utc`，以及 `gex/vanna/charm/atm_iv/svol_state/svol_corr`
  - `build_active_options_input_snapshot()` 会记录 L1 `computed_gamma/computed_vanna/computed_iv/computed_delta` 对 Active Options 输入的覆盖计数
  - housekeeping 在 Active Options 更新后会记录 top rows 的 `flow/flow_score/flow_signal_state`
- Verification:
  - `python -m py_compile l1_compute/reactor.py l1_compute/reactor_support.py shared/services/active_options/input_adapter.py app/loops/housekeeping_loop.py l1_compute/tests/test_reactor.py shared/services/active_options/test_input_adapter.py app/loops/tests/test_housekeeping_gpu_dedup.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 tests/l0_runtime/test_arrow_roundtrip.py tests/l0_runtime/test_option_chain_builder_rust_events.py tests/l0_runtime/test_fetch_chain_components.py l1_compute/tests/test_reactor.py shared/services/active_options/test_input_adapter.py app/loops/tests/test_housekeeping_gpu_dedup.py`

## Risks / Constraints
- Risk 1: 本次证明的是 Arrow/L0 metadata -> L1 -> Active Options 的合同与数据流诊断可见性，未直接对实盘联网 feed 做长时间在线验证。
- Risk 2: Active Options 最终 flow 日志位于 `housekeeping_loop`，属于下游共享服务路径，不在 L1 reactor 本体内计算。

## Next Action
- Immediate Next Step: 同步 handoff/meta/context 并跑 `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` 直到通过。
- Owner: Codex

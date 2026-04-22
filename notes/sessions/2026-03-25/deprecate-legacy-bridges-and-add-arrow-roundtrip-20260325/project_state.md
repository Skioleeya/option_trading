# Project State

## Snapshot
- DateTime (ET): 2026-03-25 16:15:02 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `70cc81b`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 完成 Arrow cutover 后遗留的最后两项：显式 deprecate legacy bridges，并补 Rust producer -> Python Arrow reader roundtrip 集成验证。
- Scope In:
  - `shared/system/rust_shm_bridge.py` deprecate 标记
  - legacy `rust_event_bridge` wrapper 去活与 active bridge 拆分
  - `tests/l0_runtime/test_arrow_roundtrip.py`
  - Windows Arrow IPC attach/reader 契约与对应 Rust test
  - SOP/OpenSpec/session/context 同步
- Scope Out:
  - 其他 ATM / frontend / branch-protection backlog

## What Changed (Latest Session)
- Files:
  - `shared/system/rust_shm_bridge.py`
  - `shared/system/ipc_reader.py`
  - `shared/services/l0_runtime/facade.py`
  - `shared/services/l0_runtime/normalize/bridges/__init__.py`
  - `shared/services/l0_runtime/normalize/bridges/market_event_bridge.py`
  - `shared/services/l0_runtime/normalize/bridges/rust_event_bridge.py`
  - `tests/l0_runtime/test_arrow_roundtrip.py`
  - `l0_ingest/l0_rust/src/gateway_core.rs`
  - `l0_ingest/l0_rust/src/ipc_legacy.rs`
  - `docs/SOP/L0_DATA_FEED.md`
  - `openspec/changes/rewrite-l0-in-rust/tasks.md`
  - `openspec/changes/rewrite-l0-in-rust/specs/l0-rust-ipc/spec.md`
- Behavior:
  - live Rust event normalization 已迁到 `market_event_bridge.py`；`rust_event_bridge.py` 仅保留 deprecated compatibility wrapper
  - `RustBridge` 现显式发出 `DeprecationWarning`，明确不再属于 `rust_only` live path
  - Arrow reader 走 Windows named mapping attach，Rust `stress_test()` 显式释放 GIL，允许真实 roundtrip 并发验证
  - roundtrip test 覆盖 batch-local `batch_id` 一致性、`arrival_mono_ns`、schema 与 symbol 合同
- Verification:
  - `cargo test`
  - `python -m py_compile ...`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 tests/l0_runtime/test_rust_event_bridge.py tests/l0_runtime/test_option_chain_builder_rust_events.py tests/l0_runtime/test_arrow_ipc_signal.py tests/l0_runtime/test_arrow_roundtrip.py`

## Risks / Constraints
- Risk 1: `ipc_legacy.rs` 仍同时承载 legacy ring buffer 兼容代码与当前 Arrow transport 底层共享映射实现；后续若继续演化，宜再拆分成更细的 transport 模块。
- Risk 2: roundtrip test 验证的是覆盖式共享段上的“可读 batch 合同”，不等价于批次队列语义，因此只断言批内 `batch_id` 一致而不假设首批一定为 `1`。

## Next Action
- Immediate Next Step: 同步 context/session 元数据并跑 `scripts/validate_session.ps1 -Strict` 直至全绿。
- Owner: Codex

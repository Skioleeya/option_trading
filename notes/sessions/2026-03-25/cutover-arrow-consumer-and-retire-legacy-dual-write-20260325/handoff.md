# Handoff

## Session Summary
- DateTime (ET): 2026-03-25 15:25:07 -04:00
- Goal: 将 L0 活跃消费面切到 Arrow IPC，并让 Rust 实时输出退场 legacy SHM dual-write。
- Outcome: `rust_only` 已改为通过 `ArrowIpcReader` 消费 `${shm_path}_arrow` 批次，`RustBridge` 已退出 live path；Rust `gateway_core.rs` 已移除 legacy SHM 双写，Arrow IPC 成为唯一热路径输出。`shm_stats.head/tail` 在 Arrow 路径下继续稳定透传，但语义改为最近消费到的 `batch_id`。

## What Changed
- Code / Docs Files:
  - `shared/services/l0_runtime/facade.py`
  - `shared/services/l0_runtime/source/runtime/quote_runtime.py`
  - `shared/services/l0_runtime/projection/snapshot/components.py`
  - `shared/services/l0_runtime/projection/snapshot/payload.py`
  - `shared/services/l0_runtime/normalize/bridges/__init__.py`
  - `shared/services/l0_runtime/normalize/bridges/arrow_batch_bridge.py`
  - `l0_ingest/l0_rust/src/gateway_core.rs`
  - `l0_ingest/l0_rust/src/helpers.rs`
  - `l0_ingest/l0_rust/src/ipc.rs`
  - `tests/l0_runtime/test_fetch_chain_components.py`
  - `tests/l0_runtime/test_quote_runtime.py`
  - `tests/l0_runtime/test_option_chain_builder_rust_events.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `docs/SOP/SYSTEM_OVERVIEW.md`
  - `docs/SOP/L1_LOCAL_COMPUTATION.md`
  - `openspec/changes/rewrite-l0-in-rust/tasks.md`
  - `openspec/changes/rewrite-l0-in-rust/specs/l0-rust-ipc/spec.md`
- Runtime / Infra Changes:
  - `OptionChainBuilder` 在 `rust_only` 模式下改读 runtime transport contract（`${shm_path}_arrow` + `${shm_path}_arrow_signal`），不再接线 `RustBridge`
  - `PythonQuoteRuntime` 继续保留 `event_queue` 作为 fallback；`RustQuoteRuntime` 新增 Arrow transport contract 暴露
  - `fetch_snapshot().shm_stats.head/tail` 改为最近消费到的 Arrow `batch_id`
  - `RustIngestGateway` 已去掉 `IpcProducer.push(...)` hot-path dual-write
- Commands Run:
  - `python -m py_compile shared/services/l0_runtime/facade.py shared/services/l0_runtime/source/runtime/quote_runtime.py shared/services/l0_runtime/projection/snapshot/components.py shared/services/l0_runtime/projection/snapshot/payload.py shared/services/l0_runtime/normalize/bridges/arrow_batch_bridge.py tests/l0_runtime/test_fetch_chain_components.py tests/l0_runtime/test_quote_runtime.py tests/l0_runtime/test_option_chain_builder_rust_events.py`
  - `cargo test`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 tests/l0_runtime/test_arrow_ipc_signal.py tests/l0_runtime/test_fetch_chain_components.py tests/l0_runtime/test_quote_runtime.py tests/l0_runtime/test_option_chain_builder_rust_events.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 tests/l0_runtime app/tests/test_health_route_diagnostics.py app/tests/test_compute_loop_timestamp.py app/loops/tests/test_compute_loop_gpu_dedup.py app/loops/tests/test_compute_loop_atm_live_continuity.py`

## Verification
- Passed:
  - `python -m py_compile shared/services/l0_runtime/facade.py shared/services/l0_runtime/source/runtime/quote_runtime.py shared/services/l0_runtime/projection/snapshot/components.py shared/services/l0_runtime/projection/snapshot/payload.py shared/services/l0_runtime/normalize/bridges/arrow_batch_bridge.py tests/l0_runtime/test_fetch_chain_components.py tests/l0_runtime/test_quote_runtime.py tests/l0_runtime/test_option_chain_builder_rust_events.py`
  - `cargo test`
  - `tests/l0_runtime/test_arrow_ipc_signal.py tests/l0_runtime/test_fetch_chain_components.py tests/l0_runtime/test_quote_runtime.py tests/l0_runtime/test_option_chain_builder_rust_events.py`
  - `tests/l0_runtime app/tests/test_health_route_diagnostics.py app/tests/test_compute_loop_timestamp.py app/loops/tests/test_compute_loop_gpu_dedup.py app/loops/tests/test_compute_loop_atm_live_continuity.py`
  - `scripts/validate_session.ps1 -Strict`
- Failed / Not Run:
  - 无

## Pending
- Must Do Next:
  - 为旧 `rust_shm_bridge` / `rust_event_bridge` 增加显式 deprecate 标记
  - 新增 `tests/l0_runtime/test_arrow_roundtrip.py`
- Nice to Have:
  - 将 `ipc.rs` 正式改名为 `ipc_legacy.rs`，让兼容壳语义更清晰

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本轮已完成 Arrow consumer cutover 与 legacy dual-write retirement；剩余 debt 仅为旧 bridge 去活与 roundtrip integration test
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-27
- DEBT-RISK: 虽然 live path 已切干净，但 legacy bridge 文件仍在仓内，且 producer→reader 端到端 roundtrip 尚未单独压测
- DEBT-NEW: 0
- DEBT-CLOSED: 2
- DEBT-DELTA: -2
- RUNTIME-ARTIFACT-EXEMPT: logs/data runtime artifacts excluded by repo policy

## How To Continue
- Start Command: `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 tests/l0_runtime`
- Key Logs: `logs/backend_runtime.current.log`
- First File To Read: `notes/sessions/2026-03-25/cutover-arrow-consumer-and-retire-legacy-dual-write-20260325/project_state.md`

## Strict Validation Output
`[OK] commands include validate_session.ps1 -Strict evidence; [OK] SOP sync gate OK; [OK] architecture anti-coupling scan passed; [OK] quality thresholds passed; [OK] openspec parent/child gate passed; [OK] debt gate passed; Session validation passed.` (2026-03-25 15:25 ET)

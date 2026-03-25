# Project State

## Snapshot
- DateTime (ET): 2026-03-25 15:25:07 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `70cc81b`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: 将 `shared/services/l0_runtime` 活跃消费面从 legacy SHM polling bridge 切到 Arrow IPC reader，并让 Rust L0 热路径退掉 legacy SHM 兼容双写。
- Scope In: `shared/services/l0_runtime/facade.py`、`shared/services/l0_runtime/source/runtime/quote_runtime.py`、snapshot diagnostics 合同、`l0_ingest/l0_rust/src/gateway_core.rs`、相关 `tests/l0_runtime/*` 与 SOP/OpenSpec/session 同步。
- Scope Out: L1 Greeks/GPU 算法改写、LongPort REST 行为改版、旧 bridge 文件彻底删除。

## What Changed (Latest Session)
- Files: `shared/services/l0_runtime/facade.py`、`shared/services/l0_runtime/source/runtime/quote_runtime.py`、`shared/services/l0_runtime/projection/snapshot/{components,payload}.py`、`shared/services/l0_runtime/normalize/bridges/{__init__,arrow_batch_bridge}.py`、`l0_ingest/l0_rust/src/{gateway_core,helpers,ipc}.rs`、`tests/l0_runtime/{test_fetch_chain_components,test_quote_runtime,test_option_chain_builder_rust_events}.py`、`docs/SOP/{L0_DATA_FEED,SYSTEM_OVERVIEW,L1_LOCAL_COMPUTATION}.md`、`openspec/changes/rewrite-l0-in-rust/{tasks.md,specs/l0-rust-ipc/spec.md}`
- Behavior: `rust_only` 路径下 `OptionChainBuilder` 已不再依赖 `RustBridge` 轮询 ring buffer，而是通过 `ArrowIpcReader` 消费 `${shm_path}_arrow` + `${shm_path}_arrow_signal`；Python fallback 仍保留 `event_queue` 路径。`fetch_snapshot().shm_stats.head/tail` 在 Arrow 路径下改为最近消费到的 `batch_id`，继续维持 L0→L4 诊断链连续。Rust `gateway_core.rs` 已移除 legacy SHM dual-write，Arrow IPC 成为唯一热路径输出。
- Verification: `cargo test` 通过；`python -m py_compile` 覆盖改动模块通过；两轮 `scripts/test/run_pytest.ps1` 回归通过；`scripts/validate_session.ps1 -Strict` 已在 2026-03-25 15:25 ET 通过。

## Risks / Constraints
- Risk 1: `shared/system/rust_shm_bridge.py` 与 legacy `rust_event_bridge` 仍在仓内，虽然已不在 `rust_only` live path，但尚未做显式 deprecate 落账。
- Risk 2: 还缺少 `tests/l0_runtime/test_arrow_roundtrip.py` 这类 producer→reader 的端到端 roundtrip 压测验证。

## Next Action
- Immediate Next Step: 进入下一轮遗留收尾，只处理 legacy bridge deprecate 标记与 Arrow IPC roundtrip integration test。
- Owner: Codex

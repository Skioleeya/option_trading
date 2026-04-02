# Project State

## Snapshot
- DateTime (ET): 2026-04-01 12:24:25 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `790471c`
- Environment:
  - Market: `OPEN/CLOSED`
  - Data Feed: `OK/DEGRADED/DOWN`
  - L0-L4 Pipeline: `OK/DEGRADED/DOWN`

## Current Focus
- Primary Goal: 硬切 Rust batch/shm config owner，并把 `openapi_bootstrap.py` / `quote_runtime.py` 的 LongPort SDK env writes 下沉为显式 SDK adapter。
- Scope In:
  - `shared/services/l0_runtime/source/runtime/*`
  - `shared/services/l0_runtime/l0_rust.py`
  - `l0_ingest/l0_rust/src/*`
  - `tests/l0_runtime/*`
- Scope Out:
  - `L1/L2/L3/app/UI`
  - broker strategy behavior
  - payload schema changes

## What Changed (Latest Session)
- Files:
  - `shared/config/api_credentials.py`
  - `shared/contracts/l0_transport.py`
  - `shared/contracts/__init__.py`
  - `shared/services/l0_runtime/source/runtime/openapi_bootstrap.py`
  - `shared/services/l0_runtime/source/runtime/factory.py`
  - `shared/services/l0_runtime/source/runtime/quote_runtime.py`
  - deleted: `shared/services/l0_runtime/source/runtime/rust_gateway_config.py`
  - deleted: `shared/services/l0_runtime/source/runtime/rust_runtime_support.py`
  - `shared/services/l0_runtime/l0_rust.py`
  - `l0_ingest/l0_rust/src/gateway_core.rs`
  - `l0_ingest/l0_rust/src/ipc_writer.rs`
  - `l0_ingest/l0_rust/src/sdk_config.rs`
  - `l0_ingest/l0_rust/src/transport_contract.rs`
  - `tests/l0_runtime/test_openapi_config_alignment.py`
  - `tests/l0_runtime/test_quote_runtime.py`
  - `tests/l0_runtime/test_market_data_gateway.py`
  - `tests/l0_runtime/test_arrow_roundtrip.py`
  - `07_PY_DELETE_TASK_LIST.md`
  - `08_RUST_REPLACEMENT_BOUNDARIES.md`
  - `09_PY_SHELL_REMOVAL_SEQUENCE.md`
  - `openspec/changes/refactor-bloat-20260401-rust-shared-l0-migration-boundary/artifacts/shared-l0-boundary-evidence.md`
- Behavior:
  - `openapi_bootstrap.py` 不再向 `LONGPORT_* / LONGBRIDGE_*` 写环境变量。
  - Rust gateway 不再依赖 `Config::from_env()`；改为 `RustIngestGateway().configure(...)` 显式注入 SDK config。
  - Arrow writer 不再读取 `L0_BATCH_* / L0_IPC_*` env；改为显式 transport inputs。
  - `shared/services/l0_runtime/l0_rust.py` 改为只加载 wheel 提取出的受控 `.pyd`。
- Verification:
  - `cargo test` passed
  - targeted pytest passed
  - OpenSpec gate pending session sync
  - strict validation pending session sync

## Risks / Constraints
- Risk 1: wheel 提取出的 `_native_generated/l0_rust.pyd` 是本地生成工件，必须通过 shim 单点加载，不能再回到旧 `_native`。
- Risk 2: `shared/services/l0_runtime/l0_rust.py` 现在是运行时加载关键点；后续若更换生成路径，需要同步修改 shim。

## Next Action
- Immediate Next Step: 同步 session/context，跑 OpenSpec chain gate 与 strict validation。
- Owner: Codex

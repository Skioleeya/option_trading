# Project State

## Snapshot
- DateTime (ET): 2026-03-25 15:07:06 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `70cc81b`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: 以 hard-cut 方式启动 `rewrite-l0-in-rust`，让 L0 主数据热路径从 Python SHM 轮询切到 Rust Arrow IPC，并开始清空 `l0_ingest` 下的 Python 运行时代码。
- Scope In: `l0_ingest/l0_rust/src/*`、L0 Arrow IPC 合同、L0 Python 迁移边界、`app/container.py` 的 L0 接线、session/OpenSpec/SOP 同步。
- Scope Out: L1 Greeks/GPU 计算重写、L2/L3/L4 行为改版、LongPort REST 全量 Rust 化。

## What Changed (Latest Session)
- Files: `app/container.py`、`shared/services/l0_runtime/**`、`shared/services/l0_support/**`、`tests/l0_runtime/*`、`tests/l0_support/*`、`l0_ingest/l0_rust/src/{gateway_core,ipc,ipc_writer,lib,schema,threat,gateway_rest,windows_signal}.rs`、`shared/system/{ipc_reader,ipc_signal}.py`、`docs/SOP/L0_DATA_FEED.md`
- Behavior: `l0_ingest` 下 Python文件已清零；活跃 runtime 迁入 `shared/services/l0_runtime`，legacy/support 模块迁入 `shared/services/l0_support`，测试迁到顶层 `tests/`；`app/container.py` 已彻底切断对 `l0_ingest` Python 包的依赖；Arrow IPC 的 Windows named-event signal 合同已通过 Rust `windows_signal.rs` 与 Python `shared/system/ipc_signal.py` 对齐落地。
- Verification: `cargo test` 通过；`python -m py_compile` 覆盖迁移后的核心 Python 模块通过；`scripts/test/run_pytest.ps1 tests/l0_support tests/l0_runtime` 全量 125 项通过。

## Risks / Constraints
- Risk 1: 活跃 Python 消费面尚未切到 `shared/system/ipc_reader.py`；Arrow IPC producer 与 Windows signal 已就绪，但现网连续性仍依赖 legacy 消费链。
- Risk 2: Rust gateway 当前仍保留 legacy SHM 兼容双写；要达到更纯粹的 Rust-only 数据面，还需在消费面切换后摘除旧桥接路径。

## Next Action
- Immediate Next Step: 进入下一轮 implementation slice，将 `shared/services/l0_runtime` 消费面切到 Arrow IPC reader，并在回归通过后退场 legacy SHM 双写。
- Owner: Codex

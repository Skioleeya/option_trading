# Project State

## Snapshot
- DateTime (ET): 2026-04-16 06:51:15 -04:00
- Branch: chore/sync-all-local-changes-20260313
- Last Commit: 6f31ce0
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED` (research_store append path failed before fix)

## Current Focus
- Primary Goal: 修复 `research/raw|feature|label` 无法落盘的根因，禁止兼容分支。
- Scope In:
  - `shared_rust_services/src/research_store.rs` 去除旧 Python 模块 import
  - `shared_rust_services/src/tactical.rs` 暴露 Rust VRP owner 供内部复用
  - 增加防回归守护测试，禁止再次引用旧路径
- Scope Out:
  - 不新增 fallback/shim
  - 不调整 EOD 分类策略阈值

## What Changed (Latest Session)
- Files:
  - shared_rust_services/src/research_store.rs
  - shared_rust_services/src/tactical.rs
  - scripts/test/test_module_structure_guards.py
  - .gitignore
  - shared_rust/services.pyd
- Behavior:
  - `ResearchFeatureStore.append_tick()` 的 `vrp_official_hv_based` 改为直接调用 Rust `compute_vrp_impl`，不再 import `shared.system.tactical_triad_logic`
  - Cargo 构建缓存目录统一到 `E:\US.market\Option_v3\tmp\cargo_target`，并加入 `.gitignore`
  - 已重建并加载最新 `shared_rust/services.pyd`，后端 strict 模式重启成功
- Verification:
  - `scripts/test/run_pytest.ps1 scripts/test/test_module_structure_guards.py -k research_store_no_legacy_tactical_import` -> 1 passed
  - `scripts/test/run_pytest.ps1 scripts/test/test_eod_task_guards.py scripts/test/test_eod_bucket_guards.py` -> 10 passed
  - `Remove-Item Env:CARGO_TARGET_DIR; cargo check --manifest-path shared_rust_services/Cargo.toml` -> passed
  - `cargo build --release --manifest-path shared_rust_services/Cargo.toml --target-dir tmp/cargo_target_runtime` -> passed
  - `scripts/ops/start_backend.ps1` -> started pid=12096; `/health`=ok
  - 日志最近 5000 行未出现 `No module named 'shared.system.tactical_triad_logic'` 与 `research_store append failed`
  - `/debug/persistence_status` 中 `research_store.write_failures=0`

## Risks / Constraints
- Risk 1: `tmp/cargo_target/release/.cargo-lock` 当前权限异常，release 构建需改用 `--target-dir tmp/cargo_target_runtime`。
- Risk 2: 当前时间 06:51 ET，research 落盘受 RTH 门禁（09:30-16:00）约束，`20260416` 当日文件需开盘后才能验证新增写入。

## Next Action
- Immediate Next Step: 09:30 ET 后再次检查 `data/research/raw|feature|label` 的 `*_20260416.parquet` 是否新增并持续更新。
- Owner: Codex

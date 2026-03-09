# Project State

## Snapshot
- DateTime (ET): 2026-03-09 11:38:00 -04:00
- Branch: master
- Last Commit: 9739a17
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED` (runtime switch完成，待盘中观察)
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 完成 Rust-only 单连接收敛并建立 OpenSpec 父子提案编排。
- Scope In:
  - 新增 OpenSpec 父提案 + 3 子提案（proposal/design/tasks/spec）。
  - `L0QuoteRuntime` 抽象与 `RustQuoteRuntime/PythonQuoteRuntime` 实现。
  - L0 关键组件（subscription/orchestrator/iv/tier2/tier3/builder）切换到 runtime 协议。
  - `main/container/lifespan` 去除 `primary_ctx` 预热注入链路。
  - Rust FFI 增补 REST API 并移除运行路径 `unwrap()`。
  - SOP 同步到 rust-only 启动与降级语义。
- Scope Out:
  - 不重写 L1/L2/L3 业务引擎。
  - 不做前端协议字段变更。

## What Changed (Latest Session)
- Files:
  - app/container.py
  - app/lifespan.py
  - main.py
  - l0_ingest/subscription_manager.py
  - l0_ingest/feeds/quote_runtime.py
  - l0_ingest/feeds/option_chain_builder.py
  - l0_ingest/feeds/feed_orchestrator.py
  - l0_ingest/feeds/iv_baseline_sync.py
  - l0_ingest/feeds/tier2_poller.py
  - l0_ingest/feeds/tier3_poller.py
  - l0_ingest/l0_rust/src/lib.rs
  - l0_ingest/l0_rust/Cargo.toml
  - l0_ingest/l0_rust/Cargo.lock
  - l0_ingest/tests/test_quote_runtime.py
  - shared/config/api_credentials.py
  - docs/SOP/L0_DATA_FEED.md
  - docs/SOP/SYSTEM_OVERVIEW.md
  - openspec/changes/rust-only-longport-single-connection/*
  - openspec/changes/rust-ffi-quote-rest-runtime/*
  - openspec/changes/python-quotecontext-decouple/*
  - openspec/changes/rust-only-cutover-cleanup/*
- Behavior:
  - 默认运行模式切到 `longport_runtime_mode=rust_only`。
  - Python L0 调度层不再依赖 `QuoteContext` 具体实现，统一经 `L0QuoteRuntime` 协议访问。
  - `main.py` 不再执行 pre-flight QuoteContext 初始化，不再注入 `primary_ctx`。
  - Rust 网关新增 REST pull FFI（quote/option_quote/option_chain_info_by_date/calc_indexes），并保持显式错误传播。
- Verification:
  - compileall 通过（主改动 Python 文件）。
  - `scripts/test/run_pytest.ps1` 定向回归通过（见 handoff）。
  - `cargo check` 与 `maturin build --release` 通过。

## Risks / Constraints
- Risk 1: 本地环境历史安装的 `l0_rust` 旧版本可能被优先加载；本次已通过本地 wheel 解压覆盖工作区模块优先级。
- Risk 2: `rust_only` 盘中稳定性仍需实盘观察（尤其 subscription refresh 后的符号收敛与 REST 限流协同）。

## Next Action
- Immediate Next Step: 运行 strict session gate，完成 notes/handoff 闭环并记录输出。
- Owner: Codex

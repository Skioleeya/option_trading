# Project State

## Snapshot
- DateTime (ET): 2026-04-23 09:13:55 -04:00
- Branch: `master`
- Last Commit: `b6ef4ff`
- Environment:
  - Market: `OPEN`
  - Data Feed: `UNKNOWN`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: 将 research persistence runtime durable owner 硬切到单文件 canonical parquet，并消除静默降级与三文件半提交根因。
- Scope In:
  - `shared_rust_services` research store owner / query / recovery
  - `l0_rust` research parquet commit primitive
  - `l3_assembly` fatal diagnostics continuity
  - `/history`、`/health` 相关回归
  - EOD archive / settle guard canonical 投影
  - SOP 与 OpenSpec 治理留痕
- Scope Out:
  - 历史旧日 raw/feature/label 离线回填
  - 前端 research API 契约扩展
  - 双写窗口或 runtime fallback

## What Changed (Latest Session)
- Files:
  - `shared_rust_services/src/research_store.rs`
  - `shared_rust_services/src/research_store_build.rs`
  - `shared_rust_services/src/research_store_query.rs`
  - `shared_rust_services/src/research_pending_labels.rs`
  - `shared_rust_services/src/research_schema.rs`
  - `shared_rust_services/src/research_store_support.rs`
  - `shared_rust_services/src/lib.rs`
  - `l0_ingest/l0_rust/src/research_store_storage.rs`
  - `l3_assembly/reactor.py`
  - `scripts/diagnostics/eod_bucket_archive.py`
  - `scripts/diagnostics/eod_bucket_research_sources.py`
  - `scripts/diagnostics/wait_for_eod_sources_settle.py`
  - `app/loops/tests/test_research_store_mm_flow_persistence.py`
  - `scripts/test/test_eod_bucket_archive.py`
  - `scripts/test/test_eod_bucket_guards.py`
  - `scripts/test/test_eod_task_guards.py`
  - `scripts/test/test_eod_archive_guards.py`
  - `docs/SOP/L3_OUTPUT_ASSEMBLY.md`
  - `openspec/changes/impl-20260423-research-persistence-canonical-cutover/*`
- Behavior:
  - runtime research 持久化切到 `research/canonical/day_YYYYMMDD.parquet`
  - `append_tick()` 对 timestamp / spot / mm_flow 执行严格校验并删除静默降级
  - pending label 恢复与启动补齐改为只从 canonical owner 重建
  - EOD archive 以 canonical 为 research runtime 输入并投影 frozen raw/feature/label
- Verification:
  - 定向 `run-pytest` 已通过
  - OpenSpec spec 结构检查已通过
  - `python manage.py validate-session --strict` 已通过
  - `python manage.py start-all` 与即时 `/health` probe 已通过

## Risks / Constraints
- Risk 1: 历史旧日若仍只有 `research/raw|feature|label` 而无 canonical，需要单独离线迁移，不能混入 runtime owner。
- Risk 2: 当前 Rust 编译 warning 未清理，但未触发 strict / 运行时行为门禁。

## Next Action
- Immediate Next Step: 如需补历史 research 日数据，另开离线 canonical 回填 session；否则本 session 可直接 handoff。
- Owner: `Codex`

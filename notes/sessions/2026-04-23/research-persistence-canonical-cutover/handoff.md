# Handoff

## Session Summary
- DateTime (ET): 2026-04-23 09:20:59 -04:00
- Goal: 一次性把 research persistence runtime durable owner 从三文件半提交模型切到单文件 canonical owner，并修掉静默降级写入。
- Outcome: 已完成 canonical owner 硬切、定向回归、strict validate、Windows 主机 `start-all` 与 `/health` 验证。

## What Changed
- Code / Docs Files:
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
- Runtime / Infra Changes:
  - runtime 只写 `research/canonical/day_YYYYMMDD.parquet`
  - invalid `data_timestamp` / `spot` / `mm_flow` 改为 fail-fast
  - pending label recovery 改为 canonical-only replay
  - EOD archive 改为从 canonical 生成 frozen `research_raw` / `research_feature` / `research_label`
- Commands Run:
  - `python manage.py build-pyd --crate shared_rust_services --crate l0_rust`
  - `python manage.py run-pytest app/loops/tests/test_research_store_mm_flow_persistence.py app/tests/test_history_routes_v2.py app/tests/test_health_route_diagnostics.py scripts/test/test_eod_bucket_archive.py scripts/test/test_eod_bucket_guards.py scripts/test/test_eod_task_guards.py scripts/test/test_eod_archive_guards.py`
  - `openspec.cmd list`
  - `rg -n "^## Purpose|^## Requirements|^#### Scenario:" openspec/changes/impl-20260423-research-persistence-canonical-cutover/specs -g "spec.md"`
  - `python manage.py validate-session --strict`
  - `python manage.py start-all`
  - `python -c "urllib.request.urlopen('http://127.0.0.1:8001/health')"`

## Verification
- Passed:
  - `python manage.py run-pytest ...` => `49 passed`
  - OpenSpec spec structure grep for `Purpose/Requirements/Scenario`
  - `python manage.py validate-session --strict` => passed after补齐 strict command evidence / debt SLA bookkeeping
  - `python manage.py start-all` => Redis `6380` / Backend `8001` / Frontend `5173` 全部 listening
  - 立即 `/health` probe => `http_status=200`, `status="ok"`, `research_persistence={"healthy": true, "fatal_error": null}`
- Failed / Not Run:
  - 无

## Pending
- Must Do Next:
  - 如需把历史旧日 `research/raw|feature|label` 回填到 canonical，另开离线迁移 session
- Nice to Have:
  - 清理当前 Rust 编译 warning

## Debt Record (Mandatory)
- DEBT-EXEMPT: no unchecked session tasks after strict validate + start-all + context sync
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-23
- DEBT-RISK: none for this session scope
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION:
- RUNTIME-ARTIFACT-EXEMPT: N/A

## How To Continue
- Start Command: `.\\.venv\\Scripts\\python.exe manage.py start-all`
- Key Logs: `notes/sessions/2026-04-23/research-persistence-canonical-cutover/handoff.md`
- First File To Read: `shared_rust_services/src/research_store.rs`

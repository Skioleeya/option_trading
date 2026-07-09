## Why

研究持久化当前存在两个不可接受的 owner 级缺陷：

1. `append_tick()` 会对非法 `data_timestamp` 回退到进程时间，并对非法 `spot` 静默跳过，导致 research 样本失真且不可追溯。
2. 运行时按 `raw -> feature -> label` 三文件顺序提交，任一阶段失败都会暴露半提交状态，破坏 `/history`、health 与 EOD archive 的 owner 一致性。

这次变更需要一次性把 durable owner 硬切到单文件 canonical parquet，消除静默丢数与多文件非原子提交根因。

## What Changes

1. `ResearchFeatureStore` 运行时 durable owner 改为 `data/research/canonical/day_YYYYMMDD.parquet`。
2. `append_tick()` 对 `payload.data_timestamp`、`snapshot.spot`、`payload.fused_signal.mm_flow` 执行严格校验，非法输入直接失败并走 fatal。
3. Rust 存储原语改为单文件整日重写 + 原子替换提交；Windows 上使用文件级替换，不再依赖目录句柄同步。
4. 启动恢复与 label continuity 改为只从 canonical owner 重建并补齐成熟 label。
5. `/api/research/features`、`/history?view=feature` 保持对外 shape 不变，但内部统一从 canonical 投影。
6. EOD archive 改为消费 canonical，并在 staging 下生成 `research_raw` / `research_feature` / `research_label` 冻结产物。
7. L3 SOP 同步为 canonical owner 语义。

## Scope

In:
- `shared_rust_services/src/research_store*.rs`
- `shared_rust_services/src/research_pending_labels.rs`
- `shared_rust_services/src/research_schema.rs`
- `l0_ingest/l0_rust/src/research_store_storage.rs`
- `l3_assembly/reactor.py`
- `scripts/diagnostics/eod_bucket_archive.py`
- `scripts/diagnostics/eod_bucket_research_sources.py`
- `scripts/diagnostics/wait_for_eod_sources_settle.py`
- `app/loops/tests/test_research_store_mm_flow_persistence.py`
- `app/tests/test_history_routes_v2.py`
- `app/tests/test_health_route_diagnostics.py`
- `scripts/test/test_eod_bucket_archive.py`
- `scripts/test/test_eod_bucket_guards.py`
- `scripts/test/test_eod_task_guards.py`
- `scripts/test/test_eod_archive_guards.py`
- `docs/SOP/L3_OUTPUT_ASSEMBLY.md`

Out:
- 历史旧日 `research/raw|feature|label` 数据的离线迁移
- 前端契约与 `/api/research/features` 返回字段集扩展
- 双写兼容窗口或 runtime fallback

## Verification Gate

1. `python manage.py run-pytest` 跑 research/history/health/EOD 定向套件通过。
2. `python manage.py validate-session --strict` 通过。
3. `python manage.py start-all` 在 Windows 主机完成健康启动证据。

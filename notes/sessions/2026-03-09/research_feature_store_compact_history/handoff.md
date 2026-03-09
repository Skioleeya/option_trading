# Handoff

## Session Summary
- DateTime (ET): 2026-03-09 16:43:38 -04:00
- Goal: 实现指标研发/调参历史数据三层持久化与历史下载体积压缩。
- Outcome: 已完成 `research_feature_store`、`/history` compact 投影改造、研究查询导出接口及回归测试。

## What Changed
- Code / Docs Files:
  - shared/services/research_feature_store.py
  - app/routes/history.py
  - l3_assembly/reactor.py
  - shared/config/persistence.py
  - l3_assembly/tests/test_research_feature_store.py
  - docs/SOP/L3_OUTPUT_ASSEMBLY.md
- Runtime / Infra Changes:
  - 新增三层研究存储（raw-lite/feature/label）与 retention 配置。
  - 新增 `GET /api/research/features`（`fields/view/interval/format`）。
  - 新增导出任务接口：`/api/research/exports/{job_id}` 与 `/download`。
  - `/history` 默认视图切为 `compact`，支持字段投影与降采样。
- Commands Run:
  - powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId research_feature_store_compact_history -Timezone "Eastern Standard Time" -ParentSession "2026-03-09/mtf_iv_window_restart_persistence"
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l3_assembly/tests/test_research_feature_store.py
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l3_assembly/tests/test_reactor.py
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l3_assembly/tests/test_assembly.py

## Verification
- Passed:
  - scripts/test/run_pytest.ps1 l3_assembly/tests/test_research_feature_store.py (4 passed)
  - scripts/test/run_pytest.ps1 l3_assembly/tests/test_reactor.py (14 passed)
  - scripts/test/run_pytest.ps1 l3_assembly/tests/test_assembly.py (28 passed)
- Failed / Not Run:
  - 无

## Pending
- Must Do Next:
  - 运行 strict gate：`powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`
- Nice to Have:
  - 将 research parquet 写入改为增量分片 + 后台 compact，降低高频 I/O。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本次按范围完成核心目标；高频写入优化留作后续性能债
- DEBT-OWNER: Codex/User
- DEBT-DUE: 2026-03-12
- DEBT-RISK: 极高频场景下 Parquet 重写策略可能放大 I/O 开销
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: DEBT-DELTA=0
- RUNTIME-ARTIFACT-EXEMPT: tmp/pytest_cache, data/research, data/mtf_iv, data/wall_migration, data/atm_decay

## How To Continue
- Start Command:
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict
- Key Logs:
  - `[ResearchFeatureStore]` / `[L3 Reactor] research_store append failed`（非致命）
- First File To Read:
  - shared/services/research_feature_store.py

# Project State

## Snapshot
- DateTime (ET): 2026-03-09 16:43:38 -04:00
- Branch: master
- Last Commit: f2268d2
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 落地研究特征库三层持久化与下载体积压缩（compact/projection/interval/parquet）。
- Scope In:
  - 新增 `research_feature_store`（raw-lite/feature/label）。
  - L3 reactor 接入研究库写入与诊断。
  - `/history` 改为默认 compact 视图，支持 `view/fields/interval/format`。
  - 新增 `/api/research/features` 与异步导出状态/下载接口。
  - 配置与 SOP 同步。
- Scope Out:
  - 不修改 L4 组件契约。
  - 不持久化每 tick 全量链路 `chain_elements/per_strike_gex`。

## What Changed (Latest Session)
- Files:
  - shared/services/research_feature_store.py
  - app/routes/history.py
  - l3_assembly/reactor.py
  - shared/config/persistence.py
  - l3_assembly/tests/test_research_feature_store.py
  - docs/SOP/L3_OUTPUT_ASSEMBLY.md
- Behavior:
  - 新增三层研究数据持久化：raw-lite(短期) / feature(中期) / label(长期)。
  - 下载接口支持字段投影、时间降采样、Parquet(ZSTD) 导出；超限查询自动异步导出。
  - `/history` 默认返回 compact，减少历史下载体积。
- Verification:
  - 新增 research store 测试通过；L3 assembly/reactor 回归通过。

## Risks / Constraints
- Risk 1: Parquet 追加采用“读旧+写新”策略，极高频场景下 I/O 成本偏高（稳定优先）。
- Risk 2: `audit` 视图目前通过 `/history` 从 L2 内存/JSONL侧读取，未并入 research parquet 分层。

## Next Action
- Immediate Next Step: 运行 strict gate：`scripts/validate_session.ps1 -Strict`。
- Owner: Codex/User

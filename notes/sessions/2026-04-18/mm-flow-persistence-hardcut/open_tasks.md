# Open Tasks

## Priority Queue
- [x] P0: MM FLOW 前向持久化硬切修复
  - Owner: Codex
  - Definition of Done: feature tier + schema/projection/spec 全链路包含 9 字段，且 append_tick 缺失时显式失败
  - Blocking: None
- [ ] P1: 历史 4.17 及更早交易日 MM FLOW 回填
  - Owner: Quant Data Ops
  - Definition of Done: 补齐可重算原始数据后，回填历史 feature parquet 并产出审计报告
  - Blocking: 历史 raw/source 数据当前缺失，无法无-fallback 重算
- [x] P2: MM FLOW 合同与持久化回归测试落地
  - Owner: Codex
  - Definition of Done: 新增 persistence/schema 同步测试并通过
  - Blocking: None

## Parking Lot
- [x] Item: compact 视图扩展 MM FLOW（本会话明确不做）
- [x] Item: 历史坏文件 `feature_20260319.parquet` 修复（非本次 P0）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] MM FLOW 持久化断点根因定位（2026-04-18 07:44 ET）
- [x] feature schema/allowlist/service spec 同步修复（2026-04-18 07:53 ET）
- [x] MM FLOW 持久化与严格失败测试通过（2026-04-18 07:57 ET）
- [x] 严格会话校验通过（2026-04-18 08:01 ET）

# Open Tasks

## Priority Queue
- [x] P0: FLOW 语义拆分（`flow` USD / `flow_score` DEG）并统一颜色语义
  - Owner: Codex
  - Definition of Done: shared->L3->L4 合同链路新增 `flow_score`，`flow_direction/flow_color` 与 `flow` 金额符号一致
  - Blocking: 无
- [x] P0: 回归覆盖（冲突符号场景 + L3 合同透传）
  - Owner: Codex
  - Definition of Done: 新增 runtime_service 单测覆盖正/负/零三类场景，L3 回归验证 `flow_score` 透传
  - Blocking: 无
- [x] P1: SOP 同步（L3/L4）
  - Owner: Codex
  - Definition of Done: 文档明确 `flow` 与 `flow_score` 语义边界，避免再次混义
  - Blocking: 无

## Parking Lot
- [ ] P1: 修复 `l3_assembly/tests/test_presenters.py::test_no_nan_inf_in_gex` 既有断言错误（`call_gex`/`put_gex` 字段漂移）
- [ ] P1: 修复 L4 本地 Vitest/构建既有异常（EPERM + no test suite found）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] FLOW 语义拆分与端到端合同修复（2026-03-10 10:05 ET）

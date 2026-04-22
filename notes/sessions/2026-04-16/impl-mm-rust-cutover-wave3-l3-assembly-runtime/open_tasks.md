# Open Tasks

## Priority Queue
- [x] P0: Full payload 显式输出 `agent_g.data.mm_flow`
  - Owner: Codex
  - Definition of Done: `FrozenPayload.to_dict()` 稳定包含 `mm_flow`，无显式字段时自动回填 `fused_signal.mm_flow`
  - Blocking: None
- [x] P0: Delta payload 输出 `changes.agent_g_data.mm_flow`
  - Owner: Codex
  - Definition of Done: `FieldDeltaEncoder` 在 mm_flow 变化时输出增量字段
  - Blocking: None
- [ ] P1: L4 消费与可视化接入
  - Owner: Codex
  - Definition of Done: selector/model/组件链路消费 `agent_g.data.mm_flow` 并有 UI 回归
  - Blocking: 新 UI 会话

## Parking Lot
- [x] None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Wave3 OpenSpec child创建（proposal/design/tasks/spec）(2026-04-16 17:59 ET)
- [x] L3 payload/delta mm_flow 合同测试通过 (2026-04-16 18:00 ET)
- [x] strict validate 通过 (2026-04-16 18:01 ET)

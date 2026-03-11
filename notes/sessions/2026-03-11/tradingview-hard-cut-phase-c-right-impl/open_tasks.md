# Open Tasks

## Priority Queue
- [x] P0: Right typed contract 链路与弱类型隔离
  - Owner: Codex
  - Definition of Done: `RightPanel` + `rightPanelModel` 建立 `payload -> store -> model -> component` 明确链路，Right 组件不直读弱类型 payload。
  - Blocking: 无
- [x] P1: ActiveOptions 稳定槽位与 FLOW 语义
  - Owner: Codex
  - Definition of Done: 固化 5 行渲染与占位、`slot_index` 稳定键语义、FLOW 符号优先配色规则。
  - Blocking: 无
- [x] P1: 回归与门禁
  - Owner: Codex
  - Definition of Done: Right 相关新增/更新测试通过，`npm --prefix l4_ui run test` 与 strict 门禁通过。
  - Blocking: 无

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Right 模块双路径入口与 typed model 实施（2026-03-11 14:26 ET）
- [x] Right 增补回归测试与全量前端测试通过（2026-03-11 14:28 ET）
- [x] strict 门禁通过（2026-03-11 14:31 ET）

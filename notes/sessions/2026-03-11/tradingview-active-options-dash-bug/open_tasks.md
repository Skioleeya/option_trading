# Open Tasks

## Priority Queue
- [x] P0: 修复 ActiveOptions `- $0` 与符号冲突显示
  - Owner: Codex
  - Definition of Done: model 层统一 FLOW 展示文本，零值不再显示 signed-zero，冲突文本回退前端数值格式化。
  - Blocking: 无
- [x] P1: 增补 ActiveOptions 回归测试
  - Owner: Codex
  - Definition of Done: 新增 signed-zero 与冲突符号测试，渲染与 model 均覆盖。
  - Blocking: 无
- [x] P1: 相关测试通过
  - Owner: Codex
  - Definition of Done: `activeOptions.model` + `activeOptions.render` 全绿。
  - Blocking: 无

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 定位根因：`flow_deg_formatted` 文本优先导致符号不一致（2026-03-11 15:56 ET）
- [x] 修复并通过回归（2026-03-11 15:57 ET）

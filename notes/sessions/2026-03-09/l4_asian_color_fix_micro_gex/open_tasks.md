# Open Tasks

## Priority Queue
- [x] P0: 修复 MicroStats / GEX Status 亚洲风格色彩语义
  - Owner: Codex
  - Definition of Done: 红涨绿跌语义在 NET GEX 与 Wall 状态映射中统一，组件不再反向硬编码
  - Blocking: 无
- [x] P1: 状态管理集中化
  - Owner: Codex
  - Definition of Done: `gexStatus.ts` 输出亚洲语义状态/tokens，`GexStatusBar.tsx` 仅消费映射
  - Blocking: 无
- [x] P1: SOP 同步
  - Owner: Codex
  - Definition of Done: L4 SOP 增加“红涨绿跌 + 统一状态管理”约束
  - Blocking: 无

## Parking Lot
- [ ] P2: 修复当前 vitest 收集异常（No test suite found / integration init error）
- [ ] P2: 增加 GexStatusBar 组件级渲染测试（色彩语义快照）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] MicroStats/GEX 亚洲语义配色与状态管理修复（2026-03-09 15:35 ET）

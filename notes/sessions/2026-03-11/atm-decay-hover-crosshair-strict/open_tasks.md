# Open Tasks

## Priority Queue
- [x] P0: 悬停凸显必须由 TradingView 十字星命中触发
  - Owner: Codex
  - Definition of Done: 仅 `point` 合法且 `hoveredSeries` 命中时高亮；无命中立即清空焦点。
  - Blocking: 无
- [x] P1: 移除最近线推断与上一焦点黏性路径
  - Owner: Codex
  - Definition of Done: `AtmDecayChart` 不再使用 inferredFamily；`resolveNextHoveredFamily` 不再回退 currentHoveredFamily。
  - Blocking: 无
- [x] P1: 回归测试与 SOP 同步
  - Owner: Codex
  - Definition of Done: `atmDecayHover.test.ts` 语义更新并通过；`docs/SOP/L4_FRONTEND.md` 与实现一致。
  - Blocking: 无

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] ATM DECAY hover strict-hit 语义修复（2026-03-11 12:36 ET）

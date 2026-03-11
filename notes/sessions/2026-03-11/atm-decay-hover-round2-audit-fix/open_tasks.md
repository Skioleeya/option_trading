# Open Tasks

## Priority Queue
- [x] P1: 修复 `point` 非法值导致 hover 焦点残留
  - Owner: Codex
  - Definition of Done: `resolveNextHoveredFamily/resolveHoveredFamily` 对 `NaN/Inf` point 返回 `null`，无残留高亮。
  - Blocking: 无
- [x] P1: 修复数据清空/无可渲染点时的焦点残留
  - Owner: Codex
  - Definition of Done: `AtmDecayChart` 在 `data=[]` 或 `anyDataLoaded=false` 时清空 `hoveredFamily` 并同步视觉状态。
  - Blocking: 无
- [x] P1: 补齐悬停对称性与复位回归测试
  - Owner: Codex
  - Definition of Done: `atmDecayHover.test.ts` 覆盖三家族对称聚焦、非法 point、数据清空复位。
  - Blocking: 无

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] ATM DECAY Hover Round 2 审计与修复落地（2026-03-11 12:23 ET）

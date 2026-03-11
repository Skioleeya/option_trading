# Open Tasks

## Priority Queue
- [x] P1: PUT/CALL/STRADDLE 悬停聚焦实现
  - Owner: Codex
  - Definition of Done: 命中家族高亮、他线弱化、离开复位。
  - Blocking: 无
- [x] P1: BOTH 模式同族双线聚焦
  - Owner: Codex
  - Definition of Done: raw+smoothed 同步高亮，其余四线同步弱化。
  - Blocking: 无
- [x] P1: 悬停逻辑可测
  - Owner: Codex
  - Definition of Done: 新增 `atmDecayHover` 单测覆盖 displayMode/hover 矩阵与复位判定。
  - Blocking: 无
- [x] P1: 修复“同 X 三家族同显”根因
  - Owner: Codex
  - Definition of Done: `hoveredSeries` 缺失但 point 有效时，使用 `seriesData` 最近像素距离推断家族，避免回落全显。
  - Blocking: 无
- [x] P1: 取消聚焦加粗
  - Owner: Codex
  - Definition of Done: 焦点系列线宽保持基线，仅通过非焦点去强调实现聚焦。
  - Blocking: 无

## Parking Lot
- [ ] 历史 build 基线问题修复（非本次范围，Owner: Codex, DUE: 2026-03-13）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] AtmDecayChart 悬停聚焦交互落地（2026-03-11 11:37 ET）
- [x] AtmDecayChart 最近线推断与无加粗修复（2026-03-11 12:01 ET）

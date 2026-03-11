# Open Tasks

## Priority Queue
- [x] P0: BREACH 首 tick 生效（urgent bypass）
  - Owner: Codex
  - Definition of Done: BREACH 不受 debounce 延迟，测试覆盖并通过。
  - Blocking: 无
- [x] P1: Micro Stats 与 Wall Migration 在 RETREAT 场景方向一致
  - Owner: Codex
  - Definition of Done: 同输入下 Micro Stats 显示 `RETREAT ↑/RETREAT ↓` 且与 Wall Migration 不冲突。
  - Blocking: 无
- [x] P1: Debounce 不得造成 RETREAT/COLLAPSE 长时间语义滞后
  - Owner: Codex
  - Definition of Done: debounce 仅作用于 PINCH/SIEGE；RETREAT/COLLAPSE 同 tick 生效并有回归。
  - Blocking: 无

## Parking Lot
- [ ] 校准 `wall_collapse_flow_intensity_threshold`（Owner: Codex, DUE: 2026-03-16, RISK: 阈值偏移影响 COLLAPSE 灵敏度）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] WALL DYN 强制一致性修复（2026-03-11 11:09 ET）

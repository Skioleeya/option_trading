# Open Tasks

## Priority Queue
- [x] P0: 修复 NET GEX 状态标签未生效根因（对象路径字符串 `gex_regime` 被误降级）
  - Owner: Codex
  - Definition of Done: `UIStateTracker` 能正确输出字符串型 `ACCELERATION/DAMPING` 且未知值 fail-fast
  - Blocking: None
- [x] P1: 移除 MicroStats 本链路 fallback
  - Owner: Codex
  - Definition of Done: `MicroStatsPresenterV2` 无 ImportError fallback，未知 NET GEX 状态直接报错
  - Blocking: None
- [x] P1: 补齐回归测试与 SOP 同步
  - Owner: Codex
  - Definition of Done: 目标测试通过，`docs/SOP/L3_OUTPUT_ASSEMBLY.md` 更新契约规则
  - Blocking: None

## Parking Lot
- [ ] 实盘联调验证 `ui_state.micro_stats.net_gex` 与前端渲染一致性（需在线后端）

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 完成根因修复与回归测试 (2026-04-13 15:31 ET)

# Open Tasks

## Priority Queue
- [ ] P1: 迁移剩余非右侧测试文件到 Vitest 全局 API 或统一 compat shim，恢复全量 `l4_ui` 测试稳定性。
  - Owner: Codex
  - Definition of Done: `npm --prefix l4_ui run test` 全量无 `No test suite found`。
  - Blocking: 无。

## Parking Lot
- [ ] Add lint-style guard to flag CALL/PUT directional hardcoding outside approved token/theme modules.
- [ ] Consider central `directionColorToken()` helper for Right/Center/Left shared model mapping.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] RightPanel 总线收敛：`rightPanelModel` 统一 normalize `tacticalTriad/skewDynamics/mtfFlow/activeOptions/netGex`。
- [x] RightPanel 稳定路径去除 `ActiveOptions` 冗余 null fallback（直接消费总线合同）。
- [x] `rightPanelModel.test.ts` 增补脏 payload 颜色语义净化断言。
- [x] 修复右侧回归测试环境：右侧相关测试从 imported vitest API 切到 globals API，并完成 7 文件回归通过（43 tests）。
- [x] Active Options audit done: directional glow semantics aligned (bearish glow switched to green), fixed-row constant centralized.

# Open Tasks

## Priority Queue
- [x] P0: Center 图表异常降级必须不影响 L4 广播消费连续性
  - Owner: Codex
  - Definition of Done: `AtmDecayChart` 在 init/update/interaction/resize 异常时进入 degraded 且不抛出未处理错误。
  - Blocking: 无
- [x] P1: 增补 Center 降级回归测试
  - Owner: Codex
  - Definition of Done: 新增 `atmDecayChart.degrade.test.tsx`，验证图表初始化失败时组件保持挂载并输出 degraded 标记。
  - Blocking: 无
- [x] P1: Phase B openspec 任务同步闭环
  - Owner: Codex
  - Definition of Done: `openspec/changes/l4-tradingview-hard-cut-phase-b-center-module/tasks.md` 全项勾选，且包含 strict 通过证据。
  - Blocking: 无

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Phase B Center 模块降级连续性实现（2026-03-11 14:02 ET）
- [x] Center + 全量前端回归通过（2026-03-11 14:02 ET）
- [x] strict 门禁复验通过（2026-03-11 14:10 ET）

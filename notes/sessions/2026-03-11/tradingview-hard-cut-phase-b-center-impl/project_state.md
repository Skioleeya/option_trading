# Project State

## Snapshot
- DateTime (ET): 2026-03-11 14:04:20 -04:00
- Branch: master
- Last Commit: d5a961a
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 实施 Phase B Center 模块独立硬切，完成异常降级连续性与 Center 回归闭环。
- Scope In:
  - `AtmDecayChart` 增加统一降级状态机（init/update/interaction/resize）。
  - 图表运行时安全 teardown，异常后保持组件挂载并提供降级可观测标记。
  - 新增 Center 降级回归测试并完成前端全量测试与 strict 校验。
- Scope Out:
  - 不改 Right/Left 面板实现。
  - 不改 L0-L3 契约语义。

## What Changed (Latest Session)
- Files:
  - docs/SOP/L4_FRONTEND.md
  - l4_ui/src/components/center/AtmDecayChart.tsx
  - l4_ui/src/components/center/__tests__/atmDecayChart.degrade.test.tsx
  - openspec/changes/l4-tradingview-hard-cut-phase-b-center-module/tasks.md
  - notes/context/project_state.md
  - notes/context/open_tasks.md
  - notes/context/handoff.md
  - notes/sessions/2026-03-11/tradingview-hard-cut-phase-b-center-impl/project_state.md
  - notes/sessions/2026-03-11/tradingview-hard-cut-phase-b-center-impl/open_tasks.md
  - notes/sessions/2026-03-11/tradingview-hard-cut-phase-b-center-impl/handoff.md
  - notes/sessions/2026-03-11/tradingview-hard-cut-phase-b-center-impl/meta.yaml
- Behavior:
  - Center 图表在 init/update/interaction/resize 任一阶段异常时，进入显式 degraded 模式，不再执行图表副作用。
  - degraded 模式提供 `data-testid="atm-chart-degraded"` 诊断层，确保页面其余模块仍可持续渲染与消费广播。
  - strict-hit 与增量回退路径保持不变。
- Verification:
  - `npm --prefix l4_ui run test -- atmDecay` -> 20 passed
  - `npm --prefix l4_ui run test` -> 136 passed
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> passed

## Risks / Constraints
- Risk 1: 当前仓库存在大量未提交改动，本次仅在 Center 边界内实施，未触碰既有非目标变更。
- Risk 2: degraded 模式为 fail-safe 保护，若引擎连续失败将持续显示降级提示，需要后续运行时监控告警配合。

## Next Action
- Immediate Next Step: 进入 Phase C（Right 模块）独立会话准备。
- Owner: Codex

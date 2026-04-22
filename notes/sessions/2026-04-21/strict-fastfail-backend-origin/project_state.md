# Project State

## Snapshot
- DateTime (ET): 2026-04-21 10:51:59 -04:00
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `3ff3ba1`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 将 ActiveOptions 的 `IMP` 显示硬切到紧凑数字单位，并移除固定两位小数渲染。
- Scope In:
  - `l4_ui/src/lib/utils.ts` 的 IMP 格式化函数。
  - `l4_ui/src/components/right/ActiveOptions.tsx` 的 IMP 渲染链路。
  - `l4_ui` 相关单测 / 集成测试。
  - `docs/SOP/L4_FRONTEND.md` 的 ActiveOptions 显示规范同步。
  - 本次 session / context 记录同步与 strict 校验。
- Scope Out:
  - 不改后端 ActiveOptions 合同。
  - 不改 FLOW / VOL 的现有语义与视觉映射。

## What Changed (Latest Session)
- Files:
  - `l4_ui/src/lib/utils.ts`
  - `l4_ui/src/lib/__tests__/utils.test.ts`
  - `l4_ui/src/components/right/ActiveOptions.tsx`
  - `l4_ui/src/components/__tests__/activeOptions.render.test.tsx`
  - `l4_ui/src/components/__tests__/rightPanelContract.integration.test.tsx`
  - `docs/SOP/L4_FRONTEND.md`
  - `notes/sessions/2026-04-21/strict-fastfail-backend-origin/*`
  - `notes/context/handoff.md`
- Behavior:
  - `IMP` 不再使用 `toFixed(2)` 固定两位小数，而是统一走前端紧凑数字单位格式化。
  - `IMP` 现在显示 `K/M/B/T` 紧凑单位且不带 `$` 前缀；占位行保持 `—`。
  - 组件与集成测试已切换到新的紧凑单位断言。
- Verification:
  - `npm --prefix l4_ui run test -- src/lib/__tests__/utils.test.ts`
  - `npm --prefix l4_ui run test -- src/components/__tests__/activeOptions.render.test.tsx`
  - `npm --prefix l4_ui run test -- src/components/__tests__/rightPanelContract.integration.test.tsx`
  - `python3 manage.py validate-session --strict`

## Risks / Constraints
- Risk 1: 当前工作区仍存在其他未提交改动，本次 session 只同步文档与记录，不回滚其他工作。
- Risk 2: 若后续继续调整紧凑格式规则，必须同步更新 `fmtImpact` 测试与 RightPanel 集成断言。

## Next Action
- Immediate Next Step: 维持 `IMP` 紧凑数字格式为前端唯一 owner，后续若继续变更数值显示需走同一条工具函数链路。
- Owner: Codex

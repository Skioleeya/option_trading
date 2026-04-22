# Project State

## Snapshot
- DateTime (ET): 2026-04-21 10:01:25 -04:00
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `3ff3ba1`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 将 MTF FLOW 的 contraction/kinetic UI 从百分比数字改为滚动条展示。
- Scope In:
  - `l4_ui/src/components/right/MtfFlow.tsx` 渲染改造。
  - `l4_ui/src/components/__tests__/rightPanelContract.integration.test.tsx` 回归断言更新。
  - `docs/SOP/L4_FRONTEND.md` 规则同步。
- Scope Out:
  - 不改 L3 输出合同字段。
  - 不改 L1/L2/L3 计算逻辑。

## What Changed (Latest Session)
- Files:
  - `l4_ui/src/components/right/MtfFlow.tsx`
  - `l4_ui/src/components/__tests__/rightPanelContract.integration.test.tsx`
  - `docs/SOP/L4_FRONTEND.md`
- Behavior:
  - MTF FLOW 三个周期的 kinetic 强度由文本百分比改为滚动条（progressbar）显示。
  - CONSENSUS 强度由文本百分比改为滚动条显示。
  - 保留原有状态标签（`EXP/CON/EQ`、`ALIGNED/SPLIT/DIVERGE`）与颜色语义。
- Verification:
  - `npm --prefix l4_ui run test -- src/components/__tests__/rightPanelContract.integration.test.tsx src/config/__tests__/runtime.test.ts` -> 6 passed

## Risks / Constraints
- 风险 1: 紧凑分辨率下滚动条高度过小可能影响可见性，需要后续视觉巡检。
- 风险 2: 该 UI 规则与旧 SOP 条目冲突，已在同次变更中同步更新 SOP。

## Next Action
- Immediate Next Step: 进行一次真实浏览器验收，确认 MTF FLOW 条形强度在当前屏幕分辨率可读。
- Owner: Codex

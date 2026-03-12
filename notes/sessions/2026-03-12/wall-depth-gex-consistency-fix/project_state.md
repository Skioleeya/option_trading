# Project State

## Snapshot
- DateTime (ET): 2026-03-12 10:22:29 -04:00
- Branch: `master`
- Last Commit: `352c306`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: 修复 Wall/Depth/GEX 三组件同 tick 数据一致性并消除 sticky 滞留。
- Scope In: `l4_ui` store sticky 语义、left stable 适配层、相关前端测试和 L4 SOP。
- Scope Out: 后端/L3 合同字段、GEX 数学公式与策略阈值。

## What Changed (Latest Session)
- Files:
  - `l4_ui/src/store/dashboardStore.ts`
  - `l4_ui/src/components/left/leftPanelModel.ts`
  - `l4_ui/src/store/__tests__/dashboardStore.test.ts`
  - `l4_ui/src/components/left/__tests__/leftPanelModel.test.ts`
  - `docs/SOP/L4_FRONTEND.md`
- Behavior:
  - `wall_migration/depth_profile` 在 `smartMergeUiState` 中接收 `[]` 时显式清空，不再沿用旧值。
  - `wall_migration/depth_profile` 在 `null/undefined`（字段缺失）时仍 sticky 兜底。
  - Left stable 适配器优先解析 canonical wall row（`label/strike/history/lights`），并兼容 legacy（`type_label/current/h1/h2`）。
- Verification:
  - `npm --prefix l4_ui run test -- src/store/__tests__/dashboardStore.test.ts src/components/left/__tests__/leftPanelModel.test.ts src/components/left/__tests__/leftPanelMode.test.tsx src/components/center/__tests__/gexStatus.test.ts` -> 4 files / 28 tests passed。

## Risks / Constraints
- Risk 1: 工作区存在多会话并行改动，本次仅触及 `l4_ui` 与一处 L4 SOP。
- Risk 2: delta payload 若错误下发空数组将即时清空左侧块（按本次明确策略执行）。

## Next Action
- Immediate Next Step: 执行 `scripts/validate_session.ps1 -Strict` 并同步 context pointer。
- Owner: Codex

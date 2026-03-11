# Project State

## Snapshot
- DateTime (ET): 2026-03-11 13:41:29 -04:00
- Branch: master
- Last Commit: d5a961a
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 执行 Phase A（Foundation）实现：端点环境化、模块开关、图表适配器边界、RUM 打点与 TS 基线清零。
- Scope In:
  - L4 runtime config 与 feature flags
  - ProtocolAdapter RUM 生命周期打点
  - AtmDecayChart 接入 ChartEngineAdapter 抽象
  - App 历史接口端点环境化与类型收敛
  - SOP 同步与验证门禁
- Scope Out:
  - 不进入 Phase B/C/D 业务重构
  - 不修改 L3->L4 wire schema

## What Changed (Latest Session)
- Files:
  - l4_ui/src/config/runtime.ts
  - l4_ui/src/components/center/chartEngineAdapter.ts
  - l4_ui/src/hooks/useDashboardWS.ts
  - l4_ui/src/adapters/protocolAdapter.ts
  - l4_ui/src/components/App.tsx
  - l4_ui/src/components/center/AtmDecayChart.tsx
  - l4_ui/src/components/right/activeOptionsModel.ts
  - l4_ui/src/components/__tests__/debugHotkey.integration.test.tsx
  - docs/SOP/L4_FRONTEND.md
  - openspec/changes/l4-tradingview-hard-cut-phase-a-foundation/tasks.md
- Behavior:
  - WS/API 端点改为环境配置驱动，移除入口硬编码。
  - 新增模块开关读取并挂载到运行时（Center/Right/Left）。
  - Center 图表初始化切换为 `ChartEngineAdapter` 边界。
  - ProtocolAdapter 接入 `markMsgReceived/markMsgProcessed/recordReconnect`。
  - 修复 L4 TypeScript 基线 4 项错误并清零。
- Verification:
  - `npx --prefix l4_ui tsc --noEmit --project l4_ui/tsconfig.json` passed
  - `npm --prefix l4_ui run test` passed (28 files, 135 tests)
  - `openspec.cmd list` 显示 `phase-a-foundation` 为 `✓ Complete`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed

## Risks / Constraints
- Risk 1: 模块开关已接入但稳定/新实现当前仍同源，真实差异将在 Phase B/C/D 引入。
- Risk 2: `openspec` telemetry 在受限网络下上报失败，不影响本地提案状态。

## Next Action
- Immediate Next Step: 进入 Phase B（Center 模块）独立实施会话。
- Owner: Codex

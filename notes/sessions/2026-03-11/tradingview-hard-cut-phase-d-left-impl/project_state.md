# Project State

## Snapshot
- DateTime (ET): 2026-03-11 14:58:02 -04:00
- Branch: master
- Last Commit: d5a961a
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 完成 Phase D（Left 模块）独立实施，落地 LeftPanel 边界、合同消费收敛与本地视觉映射防倒灌。
- Scope In:
  - 新增 `LeftPanel` 入口并支持 `v2/stable` 独立切换。
  - 新增 `leftPanelModel`，固定 Left 的 typed contract 派生链路。
  - Left 三组件补 `preferProp`（默认保持旧行为），`stable` 路径显式启用 props 优先。
  - `wallMigrationTheme` 改为本地白名单视觉映射，忽略后端样式字段注入。
  - 增补 Left 单测/集成测试并完成全量前端回归。
- Scope Out:
  - 不改 Center/Right 业务逻辑。
  - 不改 L0-L3 运行时代码。

## What Changed (Latest Session)
- Files:
  - l4_ui/src/components/App.tsx
  - l4_ui/src/components/left/LeftPanel.tsx
  - l4_ui/src/components/left/leftPanelModel.ts
  - l4_ui/src/components/left/WallMigration.tsx
  - l4_ui/src/components/left/DepthProfile.tsx
  - l4_ui/src/components/left/MicroStats.tsx
  - l4_ui/src/components/left/wallMigrationTheme.ts
  - l4_ui/src/components/left/__tests__/leftPanelModel.test.ts
  - l4_ui/src/components/left/__tests__/leftPanelMode.test.tsx
  - l4_ui/src/components/left/__tests__/wallMigrationTheme.test.ts
  - openspec/changes/l4-tradingview-hard-cut-phase-d-left-module/tasks.md
  - docs/SOP/L4_FRONTEND.md
- Behavior:
  - Left 面板具备独立模块入口与 `v2/stable` 开关回退路径。
  - `stable` 模式通过 `leftPanelModel` 注入 typed contracts，不依赖 Center/Right 内部实现。
  - WallMigration 视觉 token 完全本地化，后端 `lights` 样式字段不再影响主视觉。
- Verification:
  - `npm --prefix l4_ui run test -- leftPanelMode leftPanelModel depthProfileNav wallMigrationTheme microStatsTheme debugHotkey` -> 17 passed
  - `npm --prefix l4_ui run test` -> 145 passed
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` -> passed

## Risks / Constraints
- Risk 1: 仓库存在既有未提交改动，本次仅触达 Left 边界与会话文档。
- Risk 2: `stable` 与 `v2` 共用 Left 组件，后续演进需保持双路径回归覆盖。

## Next Action
- Immediate Next Step: 进入下一阶段任务或提交本次会话变更。
- Owner: Codex

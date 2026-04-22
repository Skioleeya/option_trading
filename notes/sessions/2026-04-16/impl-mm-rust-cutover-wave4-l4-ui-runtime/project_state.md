# Project State

## Snapshot
- DateTime (ET): 2026-04-16 18:20:11 -04:00
- Branch: chore/sync-all-local-changes-20260313
- Last Commit: e91cff0
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED` (Wave4 L4 integration完成，strict gate已通过；仍存在既有 ActiveOptions 全量测试失败)

## Current Focus
- Primary Goal: 完成 Wave4 的 L4 `mm_flow` typed contract 消费与展示链路。
- Scope In:
  - `mmFlowModel` 合同归一化
  - `MmFlowCard` 组件渲染与 stable/default 模式接入
  - L4 model/render 定向单测与右栏回归
  - OpenSpec Wave4 与 L4 SOP 同步
- Scope Out:
  - L0-L3 计算/聚合逻辑改写
  - ActiveOptions 既有失败用例治理

## What Changed (Latest Session)
- Files:
  - l4_ui/src/components/right/mmFlowModel.ts
  - l4_ui/src/components/right/MmFlowCard.tsx
  - l4_ui/src/components/right/rightPanelModel.ts
  - l4_ui/src/components/right/RightPanel.tsx
  - l4_ui/src/components/__tests__/mmFlowModel.test.ts
  - l4_ui/src/components/__tests__/mmFlowCard.render.test.tsx
  - docs/SOP/L4_FRONTEND.md
  - openspec/changes/impl-20260416-mm-rust-cutover-wave4-l4-ui-runtime/*
- Behavior:
  - Right Panel 新增 `MM FLOW` 卡片，优先消费 `agent_g.data.mm_flow`，缺失时回退 `fused_signal.mm_flow`。
  - stable/default 两条渲染路径均可读取同一 typed `mmFlow` contract。
- Verification:
  - L4 定向测试通过（mmFlow model/render + right-panel regression）
  - 全量 `l4_ui` 测试存在既有 2 处失败（`activeOptions.render.test.tsx`），与本次 mm_flow 改动无关
  - strict validation (`scripts/validate_session.ps1 -Strict`) 通过

## Risks / Constraints
- Risk 1: 全量前端测试仍有既有失败，需要后续独立会话治理 ActiveOptions 排序/槽位问题。
- Risk 2: 工作区存在大量并行改动，本会话仅覆盖 Wave4 文件集。

## Next Action
- Immediate Next Step: 进入下一会话处理 ActiveOptions 既有全量测试失败并恢复前端全绿。
- Owner: Codex

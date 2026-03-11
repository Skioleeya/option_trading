# Project State

## Snapshot
- DateTime (ET): 2026-03-11 15:57:46 -04:00
- Branch: master
- Last Commit: d5a961a
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `VERIFIED`
  - L0-L4 Pipeline: `VERIFIED`

## Current Focus
- Primary Goal: 诊断并修复 Active Options 前端显示过多 `-`（尤其 `- $0`）的问题。
- Scope In:
  - 定位 `flow_deg_formatted` 与标准化 `flow` 符号不一致导致的展示异常。
  - 在 model 层统一 FLOW 文本语义，避免 signed-zero 与符号冲突文本泄露到 UI。
  - 增补 model/render 回归测试。
- Scope Out:
  - 不改后端 L3 payload 生产逻辑。
  - 不改 Active Options 固定 5 槽位占位策略。

## What Changed (Latest Session)
- Files:
  - l4_ui/src/components/right/activeOptionsModel.ts
  - l4_ui/src/components/__tests__/activeOptions.model.test.ts
  - l4_ui/src/components/__tests__/activeOptions.render.test.tsx
- Behavior:
  - 当 `flow=0` 时，强制展示中性 `$0`，不再出现 `- $0`。
  - 当后端 `flow_deg_formatted` 与数值 `flow` 符号冲突时，丢弃该文本并回退到前端数值格式化。
  - 固定 5 槽位占位行 `—` 行为保持不变（属于契约，不是 bug）。
- Verification:
  - `npm --prefix l4_ui run test -- activeOptions.model activeOptions.render` -> 2 files, 16 tests passed

## Risks / Constraints
- Risk 1: 若上游持续发送冲突 `flow_deg_formatted` 文本，当前策略会自动回退前端格式化文本。
- Risk 2: 本次未改后端字段来源，仅保证前端展示与数值语义一致。

## Next Action
- Immediate Next Step: 在真实行情窗口观察 `FLOW` 近零场景，确认不再出现 `- $0`。
- Owner: Codex

# Project State

## Snapshot
- DateTime (ET): 2026-03-10 10:11:38 -04:00
- Branch: master
- Last Commit: 368c9b9
- Environment:
  - Market: `NOT_VERIFIED`
  - Data Feed: `NOT_VERIFIED`
  - L0-L4 Pipeline: `NOT_VERIFIED`

## Current Focus
- Primary Goal: 修复 ActiveOptions FLOW 语义混用，确保颜色严格跟随显示金额符号并新增 `flow_score` 独立透传。
- Scope In:
  - shared active_options runtime 输出 `flow`(USD) 与 `flow_score`(DEG) 拆分。
  - L3 `ActiveOptionRow` 合同新增 `flow_score` 并保持向下兼容默认值。
  - L4 `ActiveOption` 类型与 model 归一化支持 `flow_score`，颜色继续由 `flow` 驱动。
  - 补充后端单测与 L3 合同测试，更新 L3/L4 SOP 文档。
- Scope Out:
  - 不改变 `impact_index` 排序逻辑。
  - 不新增前端显示列（`flow_score` 仅做契约字段保留）。

## What Changed (Latest Session)
- Files:
  - shared/services/active_options/runtime_service.py
  - shared/services/active_options/test_runtime_service.py
  - l3_assembly/events/payload_events.py
  - l3_assembly/presenters/active_options.py
  - l3_assembly/assembly/payload_assembler.py
  - l3_assembly/tests/test_presenters.py
  - l3_assembly/tests/test_reactor.py
  - l4_ui/src/types/dashboard.ts
  - l4_ui/src/components/right/activeOptionsModel.ts
  - l4_ui/src/components/__tests__/activeOptions.model.test.ts
  - l4_ui/src/components/__tests__/rightPanelContract.integration.test.tsx
  - docs/SOP/L3_OUTPUT_ASSEMBLY.md
  - docs/SOP/L4_FRONTEND.md
- Behavior:
  - `flow` 改为 USD signed amount；`flow_score` 承载 DEG 分数。
  - `flow_direction/flow_color` 统一由 `flow` 金额符号派生，不再由 DEG 分数驱动。
  - L4 model 对 `flow_color` 继续做方向一致性纠偏，`flow_score` 仅透传保存。
- Verification:
  - L3 reactor/payload 回归通过；新增 runtime_service 语义单测通过。
  - L4 Vitest 在当前环境存在既有框架问题（EPERM/No test suite found），已记录为非本次引入。
  - strict gate 通过：`scripts/validate_session.ps1 -Strict`。

## Risks / Constraints
- Risk 1: L4 测试环境存在既有 Vitest/构建异常，可能掩盖 UI 层回归信号。
- Risk 2: `l3_assembly/tests/test_presenters.py` 存在既有无关失败（`DepthProfileRow.call_gex` 属性断言）。

## Next Action
- Immediate Next Step: 执行 `scripts/validate_session.ps1 -Strict`，按首个失败门禁循环修复直至通过。
- Owner: Codex

PARENT_CHANGE_ID: impl-20260416-mm-rust-cutover-parent
DEPENDENCY_ORDER: 4
BLOCKED_BY: impl-20260416-mm-rust-cutover-wave3-l3-assembly-rust-runtime

## Why

Wave3 已把 `agent_g.data.mm_flow` 合同稳定暴露到 L3 full/delta，但 L4 Right 面板尚未形成 typed contract 消费与可观测渲染。Wave4 目标是仅在 L4 层完成低耦合消费，不引入跨层计算回流。

## What Changes

1. 新增 `mmFlowModel`，统一读取 `agent_g.data.mm_flow`（缺失时回退 `fused_signal.mm_flow`）并做展示归一化。
2. 新增 `MmFlowCard`，展示 Net Delta / Net Gamma / Residual Delta / OI 参与率 / 抑制偏置 / 计数器。
3. `rightPanelModel` 与 `RightPanel` 接入 typed `mmFlow` contract（stable/default 双路径）。
4. 新增 L4 单测覆盖 model 与 render 路径。
5. 更新 L4 SOP，明确 MM FLOW 卡片合同消费优先级。

## Scope

In:
- `l4_ui/src/components/right/mmFlowModel.ts`
- `l4_ui/src/components/right/MmFlowCard.tsx`
- `l4_ui/src/components/right/rightPanelModel.ts`
- `l4_ui/src/components/right/RightPanel.tsx`
- `l4_ui/src/components/__tests__/mmFlowModel.test.ts`
- `l4_ui/src/components/__tests__/mmFlowCard.render.test.tsx`
- `docs/SOP/L4_FRONTEND.md`

Out:
- L4 样式体系重构
- L2/L3 字段新增（Wave2/Wave3 已覆盖）

## Verification Gate

1. `mmFlowModel` 与 `MmFlowCard` 单测通过。
2. Right Panel 定向回归测试通过。
3. strict validate 通过。

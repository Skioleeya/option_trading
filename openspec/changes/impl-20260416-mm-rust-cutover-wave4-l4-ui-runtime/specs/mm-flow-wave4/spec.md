## Purpose

定义 Wave4 的 L4 合同消费规范：将 L3 的 `mm_flow` 字段稳定映射为 Right Panel `MM FLOW` 可视化卡片。

## Requirements

### Requirement: L4 Must Consume MM Flow From Stable Contract Path

#### Scenario: Right Panel Renders MM Flow Card

WHEN L4 收到 dashboard payload
THEN `MmFlowCard` 必须优先读取 `agent_g.data.mm_flow`
AND 当该字段缺失时仅允许回退 `agent_g.data.fused_signal.mm_flow`。

### Requirement: L4 Must Keep MM Rendering Logic Purely Presentational

#### Scenario: Model Normalizes Contract Values

WHEN `mmFlowModel` 归一化数值
THEN 非有限值必须回落 `0`
AND 方向标签必须仅由 `flow_dominance_ratio` 映射为 `SUPPRESSIVE/EXPANSIVE/BALANCED`。

### Requirement: Stable Mode Must Use Typed Contracts

#### Scenario: RightPanel Uses Stable Contracts

WHEN `RightPanel` 以 `mode=stable` 渲染
THEN `MmFlowCard` 必须接收 `rightPanelModel` 派生的 `mmFlow` typed contract
AND 不得直接依赖其它 panel 的内部状态。

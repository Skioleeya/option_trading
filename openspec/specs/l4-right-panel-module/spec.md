# l4-right-panel-module Specification

## Purpose
TBD - created by archiving change l4-tradingview-hard-cut-phase-c-right-module. Update Purpose after archive.
## Requirements
### Requirement: Right Module Typed Consumption
Right 模块 SHALL 仅消费 model 层规范化输出，不得在组件层直接处理原始 payload 弱类型字段。

#### Scenario: Weak-Typed Payload Access
- **WHEN** 组件直接读取未规范化的 `payload.agent_g...` 字段
- **THEN** 该实现 MUST 视为边界违规。

### Requirement: ActiveOptions Fixed Slots
`ActiveOptions` SHALL 始终输出 5 行稳定槽位并支持占位补齐。

#### Scenario: Backend Sends Fewer Rows
- **WHEN** 后端返回少于 5 条合约
- **THEN** 前端 MUST 补齐占位行并保持稳定 `slot_index`。

### Requirement: Flow Sign Priority
FLOW 展示语义 SHALL 以数值符号为最高优先级。

#### Scenario: Direction Text Mismatch
- **WHEN** `flow < 0` 但后端 direction/color 文本与符号不一致
- **THEN** 前端 MUST 按负值语义渲染为 BEARISH 颜色。


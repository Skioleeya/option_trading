## ADDED Requirements

### Requirement: Left Module Isolation
Left 模块 SHALL 独立实施并保持与 Center/Right 解耦，禁止跨模块嵌套实现。

#### Scenario: Nested Cross-Module Delivery
- **WHEN** Left 子提案包含 Center 或 Right 实现逻辑
- **THEN** 该子提案 MUST 被阻断并拆分。

### Requirement: Contract-Only Consumption
Left 模块 SHALL 仅消费 L3 合同字段，不得依赖 L1/L2 内部实现细节。

#### Scenario: Internal Engine Dependency
- **WHEN** Left 组件引入 L1/L2 运行时实现模块
- **THEN** 该实现 MUST 视为边界违规。

### Requirement: Local Visual Mapping
Left 模块视觉语义 SHALL 由前端本地映射控制。

#### Scenario: Backend Style Injection
- **WHEN** 后端下发样式类名与本地映射冲突
- **THEN** 前端 MUST 优先本地白名单映射以保证一致视觉语义。

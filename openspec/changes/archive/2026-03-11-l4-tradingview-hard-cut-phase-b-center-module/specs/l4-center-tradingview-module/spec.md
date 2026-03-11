## ADDED Requirements

### Requirement: Center Module Isolation
Center 图表模块 SHALL 独立实现并通过适配器边界接入，不得耦合 Right/Left 业务逻辑。

#### Scenario: Center-Only Delivery
- **WHEN** 执行 Phase B
- **THEN** 变更 MUST 限定在 Center 相关组件/模型/适配器范围。

### Requirement: Strict Hit Semantics
Center hover 交互 SHALL 严格依赖 TradingView 命中结果。

#### Scenario: Missing Hovered Series
- **WHEN** 事件存在有效 point 但缺失 `hoveredSeries`
- **THEN** 焦点 MUST 立即清空，禁止最近线推断与焦点黏性回退。

### Requirement: Degraded Rendering Continuity
Center 图表失败时 SHALL 显式降级且不得中断 L4 其余模块渲染与广播消费。

#### Scenario: Chart Engine Error
- **WHEN** 图表引擎初始化或更新异常
- **THEN** 页面 MUST 维持其余面板更新并输出可观测诊断。

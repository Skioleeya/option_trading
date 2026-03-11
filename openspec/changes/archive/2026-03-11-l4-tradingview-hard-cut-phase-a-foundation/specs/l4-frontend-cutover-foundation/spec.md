## ADDED Requirements

### Requirement: Runtime Endpoint Configurability
L4 runtime SHALL 通过环境变量配置 WS/API 端点，不得在业务入口硬编码本地地址。

#### Scenario: Environment Override
- **WHEN** 部署环境设置 `VITE_L4_WS_URL` 与 `VITE_L4_API_BASE`
- **THEN** 前端 MUST 使用该配置建立连接与历史请求。

### Requirement: Module Feature Gates
L4 SHALL 提供模块级切换开关用于分阶段灰度与快速回退。

#### Scenario: Module Rollback
- **WHEN** `VITE_L4_ENABLE_CENTER_V2=false`
- **THEN** Center 模块 MUST 回退到稳定实现且不影响 Right/Left 渲染。

### Requirement: Chart Adapter Decoupling
Center 图表模块 SHALL 依赖 `ChartEngineAdapter` 抽象，不直接绑定具体引擎实现细节。

#### Scenario: Engine Selection
- **WHEN** 图表引擎键为 `lightweight`
- **THEN** 系统 MUST 通过适配器注册机制加载实现，而非在组件中硬编码分支。

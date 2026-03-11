## Context

`useDashboardWS` 和 `App` 仍包含本地地址硬编码。硬切需要“可切换、可回退、可观测”的基础层能力，否则后续模块切换缺乏统一控制平面。

## Decisions

1. 端点配置集中化：`VITE_L4_WS_URL`、`VITE_L4_API_BASE`。
2. 模块开关集中化：`VITE_L4_ENABLE_CENTER_V2`、`VITE_L4_ENABLE_RIGHT_V2`、`VITE_L4_ENABLE_LEFT_V2`、`VITE_L4_CHART_ENGINE`。
3. 图表引擎边界化：Center 仅依赖 `ChartEngineAdapter` 接口，不依赖具体引擎实现细节。
4. 可观测性补齐：WS 收包/处理/重连事件统一打点。
5. 编译基线锁定：`tsc --noEmit` 必须零错误后进入下一阶段。

## Boundary Constraints

- 禁止 Right/Left 模块行为改动。
- 禁止引入跨层反向依赖。
- 禁止在基础层引入业务逻辑嵌套。

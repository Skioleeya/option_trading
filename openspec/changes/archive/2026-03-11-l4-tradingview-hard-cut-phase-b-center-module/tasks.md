## 1. Adapterized Center Chart

- [x] 1.1 将 Center 图表入口改造为 `ChartEngineAdapter` 调度。
- [x] 1.2 保持 `displayMode`、markers、hover 状态行为等价。

## 2. Interaction and Data Path

- [x] 2.1 固化 strict-hit 规则（无 `hoveredSeries` 必清空焦点）。
- [x] 2.2 优化增量路径并保留全量回退机制。
- [x] 2.3 校验无可渲染数据时焦点复位与初始化状态复位。

## 3. Degrade and Verification

- [x] 3.1 图表异常降级不影响 L4 广播消费连续性。
- [x] 3.2 增补/更新 Center 回归测试。
- [x] 3.3 `npm --prefix l4_ui run test`、`scripts/validate_session.ps1 -Strict` 通过。

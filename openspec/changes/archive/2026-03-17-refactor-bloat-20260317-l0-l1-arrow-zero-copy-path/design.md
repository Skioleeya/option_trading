## Design Summary

采用“兼容优先、逐步切换”的性能改造路径：

1. 在 L0 侧提供可选 Arrow 快照输出。
2. L1 优先消费 Arrow 输入，保留现有 list 回退。
3. 增加轻量性能观测（转换次数/耗时）验证收益。

## Constraints

- 不改变 `EnrichedSnapshot` 合同字段语义。
- 不移除现有回退路径。
- 任何阶段失败都可切回兼容路径。

## Hard Governance Prohibitions

- 禁止使用复杂函数：拆分为小步函数。
- 禁止使用魔法数字：阈值/开关全部命名。
- 禁止使用复杂嵌套：控制流扁平化。
- 禁止模块耦合：仅在 L0/L1 边界内实现。

## Validation Plan

- 单测覆盖 Arrow 直通 + list 回退双路径
- 记录转换次数与耗时对比
- `scripts/validate_session.ps1 -Strict`

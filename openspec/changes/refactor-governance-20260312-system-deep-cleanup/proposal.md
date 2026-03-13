## Why

当前仓库长期迭代后出现四类高风险工程债务：深层嵌套、跨层依赖耦合、功能臃肿、业务魔法数散落。若继续以单点修补推进，会放大 L0-L4 合同漂移与热路径延迟风险。

本提案将“系统深度清理”治理化为父提案 + 四个子提案，确保每次改动都可审计、可回滚、可量化。

## What Changes

父提案仅定义治理框架和门禁，不直接落地业务逻辑重构：

1. 固化四个主题子提案：`dependency -> nesting -> bloat -> magic-number`。
2. 统一量化指标口径与阈值（复杂度/嵌套/长度/重复率/魔法数）。
3. 规定每个子提案都必须完成边界扫描、测试与 strict 收口。
4. 规定父提案在最后汇总 before/after 对比并执行严格校验。

## Scope

- OpenSpec 治理编排、依赖顺序、风险与回滚策略。
- 不在父提案阶段直接提交运行时代码。

## Child Proposals

- `refactor-dependency-20260312-layer-decouple` (order 1)
- `refactor-nesting-20260312-core-loops` (order 2)
- `refactor-bloat-20260312-service-split` (order 3)
- `refactor-magic-number-20260312-constants-governance` (order 4)

## Rollback

任一子提案触发以下条件之一，立即停止后续阶段并回退到最近一个已验证阶段：

- 出现层级边界违规 import
- 回归测试失败或 strict gate 失败
- 合同字段语义被隐式改变且无迁移说明
- 指标改善不达标且无豁免审批记录

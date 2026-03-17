## Design Summary

父提案只做治理编排，不直接承载业务逻辑实现：

1. 冻结 L0-L2 热点基线（函数长度、CC、nesting、调用耗时/次数）。
2. 子提案 A 拆分 AgentG 决策管线，保持 `AgentG.decide()` 契约不变。
3. 子提案 B 拆平 IVBaselineSync 批处理流，保持 warm_up/staggered 语义不变。
4. 合并门禁要求：边界、质量、strict 三门同绿。

## Hard Prohibitions

- 禁止模块耦合
- 禁止复杂嵌套
- 禁止复杂函数
- 禁止魔法数字
- 禁止垃圾代码

## Validation Strategy

- 先子提案局部验证，再父提案 Merge Gate 汇总。
- 必须记录 before/after：
  - 函数长度
  - cyclomatic complexity
  - nesting depth
  - 批处理调用耗时/次数

## Evidence Contract

父提案收口报告必须包含：

- 两子提案 DoD 证据
- 关键回归测试结果
- `validate_session -Strict` 输出摘要
- 未闭环债务记录（若存在）

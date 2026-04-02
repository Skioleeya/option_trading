## Design Summary

父提案只定义治理骨架，不定义实现细节：

1. ActiveOptions 输入路径采用单源治理（ComputeLoop 发布，Housekeeping 仅消费）。
2. 编排层不得承担跨层源选择策略。
3. 所有实现均通过子提案落地并接受统一门禁。

## Governance Boundary

- 允许：定义顺序、风险、回滚、验证门禁。
- 禁止：在父提案中写入运行时代码级实现决策。
- 必须：子提案显式声明四项禁止规则（复杂函数、魔法数字、复杂嵌套、模块耦合）。

## Validation Plan

- 结构验证：OpenSpec 父子链路字段完整（Parent/Child headers）。
- 过程验证：任务分阶段执行，阶段证据可审计。
- 收口验证：`scripts/validate_session.ps1 -Strict` 通过并在 handoff 留痕。

## Dependency Map Evidence

### Before

- ActiveOptions 输入治理依赖零散，编排层容易被迫承担策略分支。

### After

- 治理层：父提案固定顺序与门禁。
- 执行层：子提案承接具体边界重构与验证闭环。

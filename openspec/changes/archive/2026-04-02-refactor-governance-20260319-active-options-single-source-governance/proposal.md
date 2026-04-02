## Why

`ActiveOptions` 当前问题暴露出一个治理缺口：输入链路来源在编排侧发生漂移时，容易出现“上游有链、下游全占位”的隐性退化。  
为避免在 `app/` 层引入跨层仲裁耦合，需要以父提案约束“单一输入源、边界清晰、回滚明确”的执行顺序。

## What Changes

本父提案只治理执行与门禁，不直接承载运行时代码实现：

1. 固化 ActiveOptions 输入治理链路采用“父提案 + 子提案”推进。
2. 明确子提案以 `dependency` 主题先行，先完成输入边界收敛，再进入后续结构优化。
3. 固化禁止项：禁止复杂函数、禁止魔法数字、禁止复杂嵌套、禁止模块耦合。
4. 固化收口门禁：测试入口、Strict 校验、SOP/handoff 证据留痕。

## Scope

- OpenSpec 治理边界、子提案依赖顺序、回滚条件、收口门禁。
- 不在父提案中直接提交运行时代码行为改动。

## Child Proposals

- `refactor-dependency-20260319-active-options-compute-loop-single-source`

## Rollback

若任一子提案触发以下任一条件，停止后续阶段并回退到上一个已验证节点：

- 出现跨层依赖回流（尤其 `app/loops` 承载业务仲裁）
- `scripts/validate_session.ps1 -Strict` 失败
- 输入快照合同出现不兼容变更且无过渡策略
- 诊断字段新增但无测试与文档证据

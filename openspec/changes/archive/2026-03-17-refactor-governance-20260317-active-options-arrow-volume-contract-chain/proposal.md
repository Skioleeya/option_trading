## Why

当前 Active Options 路径在 `L1 Arrow -> Housekeeping -> RuntimeService` 之间存在合同断裂风险：

1. `current_volume/turnover` 未稳定贯通到 L1 Arrow 合同，导致下游在低活跃时更容易被 `min_volume` 误过滤。
2. `ActiveOptionsRuntimeService` 仅基于 `volume` 过滤，无法利用 `current_volume` 回退语义。
3. 该问题跨越 L0/L1/app/shared，多点修补容易引入耦合和行为漂移。

因此采用父提案 + 子提案治理链路，先锁定合同与边界，再按依赖顺序落地。

## What Changes

1. 建立父提案治理框架，统一执行顺序、验收门槛、回滚策略。
2. 建立四个子提案链：dependency -> nesting -> bloat -> magic-number。
3. 在治理层强制禁令：禁止耦合、禁止复杂嵌套、禁止复杂函数、禁止垃圾代码。

## Hard Governance Prohibitions

- 禁止模块耦合：不得新增跨层逆向依赖，不得绕过中立边界。
- 禁止复杂嵌套：核心路径优先 guard clause，禁止深层分支堆叠。
- 禁止复杂函数：函数保持短小可审计，禁止“大一统”多职责函数。
- 禁止垃圾代码：禁止临时补丁残留、重复逻辑、无语义命名、静默失败分支。

## Scope

- 本父提案负责治理编排、阶段门禁与证据收口。
- 本父提案不直接修改 runtime 行为代码。

## Child Proposals

- `refactor-dependency-20260317-active-options-arrow-volume-turnover-continuity` (order 1, blocked_by: none)
- `refactor-nesting-20260317-active-options-filter-guard-flattening` (order 2, blocked_by: refactor-dependency-20260317-active-options-arrow-volume-turnover-continuity)
- `refactor-bloat-20260317-active-options-runtime-service-module-split` (order 3, blocked_by: refactor-nesting-20260317-active-options-filter-guard-flattening)
- `refactor-magic-number-20260317-active-options-threshold-constants-governance` (order 4, blocked_by: refactor-bloat-20260317-active-options-runtime-service-module-split)

## Rollback

任一子提案出现以下任一情况立即中止并回退到上一个已验证状态：

- 命中跨层违规 import 或边界扫描失败。
- 合同字段语义发生未声明变更。
- 质量门禁或 strict 校验失败。
- 治理禁令（禁止耦合/复杂嵌套/复杂函数/垃圾代码）被破坏。

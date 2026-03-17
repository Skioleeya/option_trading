## Why

多次重构后，L0-L2 仍存在热点函数/深层分支，影响可维护性与回归稳定性：

1. `l2_decision/agents/agent_g.py::_decide_impl` 体积与分支密度过高。
2. `l0_ingest/feeds/iv_baseline_sync.py::warm_up/_staggered_sync` 嵌套深、重复解析多。

本父提案用于建立 P1 去混乱治理链：先做“降复杂度 + 行为等价”，再在后续阶段冲刺硬阈值。

## What Changes

1. 建立父提案 `refactor-governance-20260317-l0-l2-dechaos-chain` 统一治理门禁与收口规则。
2. 建立 P1 子提案 A（bloat）：`refactor-bloat-20260317-l2-agentg-decision-pipeline-split`。
3. 建立 P1 子提案 B（nesting）：`refactor-nesting-20260317-l0-ivbaselinesync-flow-flattening`。
4. 所有子提案强制遵守禁止项：复杂函数、魔法数字、复杂嵌套、模块耦合、垃圾代码。

## Governance Contract

- 子提案必须通过：
  - `scripts/policy/check_layer_boundaries.ps1`
  - `scripts/policy/check_quality_gates.py`
  - `scripts/validate_session.ps1 -Strict`
- L0-L2 对外契约不变：输出字段与语义不得漂移。
- 变更必须可回滚、可审计、可量化（before/after 指标留痕）。

## Child Proposals

- `refactor-bloat-20260317-l2-agentg-decision-pipeline-split` (order 1)
- `refactor-nesting-20260317-l0-ivbaselinesync-flow-flattening` (order 2)

## Rollback

若出现任一情况，立即停止并回滚到上一个已验证提交：

- 跨层违规 import / 边界扫描失败
- 行为回归（关键分支输出漂移）
- strict 或 quality gate 失败
- 禁止项违规（复杂函数/嵌套/魔法数字/耦合）

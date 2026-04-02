PARENT_CHANGE_ID: refactor-governance-20260319-active-options-single-source-governance
DEPENDENCY_ORDER: 1
BLOCKED_BY: none

## Why

`ActiveOptions` 输入在编排层存在来源漂移风险：若 Housekeeping 承担 L1/L0 源仲裁，会形成跨层依赖与策略耦合。  
需要通过 dependency 子提案，将输入发布责任收敛到 ComputeLoop，Housekeeping 仅消费共享输入快照。

## What Changes

1. 定义 `SharedLoopState` 的 ActiveOptions 单源输入快照合同。
2. 约束 ComputeLoop 为唯一输入生产者，Housekeeping 为纯消费者。
3. 去除 Housekeeping 内跨层源仲裁职责，避免 app 层业务耦合。
4. 新增 shared 中立输入适配器（L1 优先融合，L0 兜底），统一 `computed_gamma/computed_vanna/computed_iv` 优先级。
5. ActiveOptions 行合同新增 `flow_signal_state/flow_signal_reason`，显式透传 `LIVE|DEGRADED` 与降级原因。
6. 增补输入通道与 ActiveOptions 诊断字段，支持退化排查与门禁验证。

## Hard Governance Prohibitions

- 禁止使用复杂函数
- 禁止使用魔法数字
- 禁止使用复杂嵌套
- 禁止模块耦合

## Scope

- 目标：`app/loops/compute_loop.py`、`app/loops/shared_state.py`、`app/loops/housekeeping_loop.py` 及相关测试与诊断面。
- 非目标：ActiveOptions 排序算法重写、L1 Greeks 算法调整。

## Parent

- `refactor-governance-20260319-active-options-single-source-governance`

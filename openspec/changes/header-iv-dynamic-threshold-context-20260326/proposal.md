## Why

标题栏当前只显示平值期权 `ATM IV` 与静态 `iv_regime`，无法回答三个盘中关键问题：

1. 当前 IV 处在近阶段历史什么水位
2. 0DTE 是否相对更长久期出现倒挂
3. 当前 IV 与价格是否发生日内背离

这会让标题栏只能提供点值，缺少动态阈值上下文。

## What Changes

1. 新增 `IV Rank (IVR)` 与 `IV Percentile (IVP)`，基于最近 `20` 个已完成交易日的收盘 ATM IV。
2. 新增期限结构上下文，主锚为 `1DTE ATM IV`，辅锚为 `.VIX.US`。
3. 新增 `120s` 窗口的 `ΔIV / ΔPrice` 关系状态。
4. 在 payload 中新增稳定字段 `agent_g.data.header_volatility`。
5. L4 标题栏保留当前 `spy_atm_iv` 主显示，只补紧凑上下文 token。

## Impact

- 影响 `shared/`, `l3_assembly/`, `l4_ui/`, `app/` 的辅助诊断、合同与渲染路径。
- 不改变现有 `spy_atm_iv`、`iv_regime`、`iv_velocity` 语义。
- 不把新指标接入 L2 决策权重。

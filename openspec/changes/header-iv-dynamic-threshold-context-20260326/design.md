## Architecture

### Auxiliary data

- L0 auxiliary path 低频拉取 `.VIX.US` quote，并归一化为 decimal IV 口径。
- L0 auxiliary path 额外拉取 `1DTE` 最近 ATM 合约双边 IV，定义为 call/put 有效值均值。
- 这两类数据通过 L0 snapshot diagnostics 进入下游元数据，不改现有主链 snapshot 语义。

### Context builder

- 新增一个中立共享服务，负责从稳定合同中计算标题栏 `header_volatility`。
- 输入包括：
  - 当前 `spot`
  - 当前 `ATM IV`
  - `1DTE ATM IV`
  - `.VIX.US` decimal IV
  - research feature store 中最近 `20` 个已完成交易日收盘 ATM IV
  - `120s` rolling `spot/ATM IV` 窗口

### Payload contract

- `agent_g.data.header_volatility` 固定包含：
  - `lookback_days`
  - `lookback_effective_days`
  - `ivr`
  - `ivp`
  - `term_structure.primary`
  - `term_structure.secondary`
  - `iv_price_relation`

### UI

- 标题栏主 IV 数值继续使用 `spy_atm_iv`
- 主色继续由 `iv_regime` 决定
- 紧凑 token 固定显示：
  - `R{ivr}`
  - `P{ivp}`
  - `1D {ratio}`
  - `VX {ratio}`
  - `β {state}`

## Definitions

- `IVR = (curr - min(hist)) / (max(hist) - min(hist)) * 100`
- `IVP = 历史中低于当前 IV 的天数 / 样本数 * 100`
- 历史窗口固定为最近 `20` 个已完成交易日，排除当前交易日
- `term_ratio_1dte = atm_iv_0dte / atm_iv_1dte`
- `term_ratio_vix = atm_iv_0dte / vix_iv_decimal`
- `ΔIV / ΔPrice` 窗口固定 `120s`

## State Rules

- 历史样本 `< 5` 时，`ivr` 与 `ivp` 返回 unavailable
- `term_structure.primary.state`
  - `INVERTED` when `ratio > 1.05`
  - `FLAT` when `0.95 <= ratio <= 1.05`
  - `NORMAL` when `ratio < 0.95`
  - `UNAVAILABLE` when 1DTE 缺失
- `iv_price_relation.state`
  - `INVERSE_CONFIRM`
  - `POSITIVE_DIVERGENCE`
  - `VOL_LEAD`
  - `PRICE_LEAD`
  - `UNAVAILABLE`
- `ΔIV / ΔPrice` 显著阈值复用现有 `spot_roc_threshold_pct` 与 `iv_roc_threshold_pct`

## Design Summary

本提案将交易日 taxonomy 重构为三层：

1. `primary_day_type`：互斥主路径标签，只表达“这一天主要如何走”
2. `context_modifiers[]`：正交修饰符，只表达“这一天在什么上下文下发生”
3. `close_profile`：必填收盘质量标签，只表达“最终收在什么位置”

目标是消除当前 taxonomy 中“路径、开盘背景、事件机制”混用导致的重叠。

## Research Basis

本设计遵循文献中的共同模式，而不是照搬交易员口语命名：

- Hamilton (1989) 与 Ang & Timmermann (2012) 将 regime 定义为统计过程或状态切换，而不是一组互相覆盖的口语化日型。
- Hendricks, Gebbie, Wilcox (2016) 以 intraday microstructure features 聚类得到 market states，说明状态标签应先由路径/特征主导，再做在线识别。
- Bucci & Ciciretti (2022) 与 Wang et al. (2020) 使用 return、volatility、covariance 等观测量识别 regimes，强调主状态应与观测统计量绑定。
- Chen & Tsang (2018) 用 directional change 指标识别正常/异常 regime，说明“方向切换”本身应是独立可测的状态维度。
- Grant, Wolf & Yu (2005) 研究 intraday reversals，说明 reversal 更适合作为事件化路径标签，而不是 trend 的子类。
- Ni, Pearson & Poteshman (2005) 研究 option-expiration pinning，说明 pinning 是事件/机制覆盖，不应与路径主标签并列。

## Canonical Output Model

分类输出应升级为：

```text
primary_day_type: trend_day | reversal_day | balance_day | whipsaw_day
context_modifiers: subset of [gap_open, high_vol_open, pinning, vol_crush]
close_profile: strong_close | mid_close | weak_close
```

其中：

- `primary_day_type` 必须唯一
- `context_modifiers` 可以多选
- `close_profile` 必须存在，且是后验质量标签，不得改变主标签
- active contract 中不得保留 `primary_tag`、`legacy_primary_tag`、`matched_tags` 等 flat compatibility 字段

## Primary Day Types

### 1. `trend_day`

定义：全天存在单一主导方向，价格大部分时间沿同一方向推进，收盘仍保留大部分位移。

实现阶段必须使用以下指标族来判定 `trend_day`：

- `abs(net_return)` 高
- `directional_efficiency` 高
- `open_side_persistence` 高
- `close_to_extreme` 低
- `state_switch_rate` 低

排除条件：

- 不得存在占主导的反向控制段
- 不得仅靠 gap 决定标签

### 2. `reversal_day`

定义：日内先沿一个方向形成有效扩展，随后出现一次主导性反转，后半段由反向控制并将收盘拉向反转方向。

实现阶段必须使用以下指标族或其等价路径派生量来判定 `reversal_day`：

- 早段存在清晰初始 excursion
- 中段或午后出现主导方向翻转
- 反转段位移显著，且不得只是轻微回吐
- `state_switch_rate` 不宜高到落入 whipsaw
- `close_profile` 只能为 `strong_close` 或 `mid_close`

关键边界：

- `reversal_day` 不是 `trend_day` 子类
- 禁止再造 `reversal_trend_day`

### 3. `balance_day`

定义：价格主要围绕公平区或关键位双向拍卖，没有稳定的单向主导控制。

实现阶段必须使用以下指标族来判定 `balance_day`：

- `abs(net_return)` 低到中等
- `directional_efficiency` 低
- `close_to_key_level` 低或 value 区停留时间高
- `pinning` 若成立，只能作为 modifier，不得改变主标签

迁移说明：

- 现有 `range_day` 直接升级命名为 `balance_day`
- 本提案采用硬切，不保留 `range_day` 兼容 alias

### 4. `whipsaw_day`

定义：存在多次方向切换、假突破或假跌破，范围可大，但主控方向不稳定。

实现阶段必须使用以下指标族来判定 `whipsaw_day`：

- `state_switch_rate` 高
- `realized_range` 高
- `directional_efficiency` 低
- 多个方向段彼此抵消

关键边界：

- `whipsaw_day` 表示“多次失控切换”
- `reversal_day` 只要求“一次主导性方向翻转”

## Context Modifiers

### `gap_open`

- 仅表达开盘相对前收存在显著跳空
- 不得决定主标签
- `gap_trend_day` 应重写为 `trend_day + gap_open`

### `high_vol_open`

- 仅表达开盘波动状态异常
- 允许与任意主标签共存

### `pinning`

- 仅表达价格围绕关键 strike / key level 被吸附
- 当 `pinning` 成立时，主标签必须由路径规则独立决定；`pinning` 不能单独决定主标签

### `vol_crush`

- 仅表达波动率塌陷机制
- 可叠加在任意 `primary_day_type`
- 禁止把“IV 下跌”直接当成独立主路径

## Close Profile

`close_profile` 用来替代未来容易重叠的组合型日名，且必须由统一 close-location 规则产出：

- `strong_close`：收盘接近日内控制方极值
- `mid_close`：收盘回到区间中后段
- `weak_close`：尾盘显著回吐，未保留控制优势

这样可以表达：

- `reversal_day + strong_close`
- `trend_day + weak_close`

而无需再引入 `reversal_trend_day`、`failed_trend_day` 等重复一级标签。

## Hard Cut Policy

实施完成后必须满足：

- active cold manifest 不得再输出 legacy flat 标签字段
- active quality report 不得再输出 legacy flat 标签字段
- classifier return payload 不得再输出 legacy flat 标签字段
- 任何仍无法 canonical 重建的历史 cold artifact，要么恢复源数据后重建，要么从 active cold archive 中退役

## Verification Plan

后续实现必须验证：

1. 任一交易日只能有一个 `primary_day_type`
2. 任一 modifier 都不改变主标签互斥性
3. `reversal_day` 与 `whipsaw_day` 在典型样本上可区分
4. active cold archive 中不再残留 legacy-only manifest 或 by_regime 索引
5. 2026-03-30 这类“上午上冲、午后下跌、尾盘回抽”的样本优先落入 `reversal_day`，而不是 `trend_day`
6. cold manifest、quality report、分类脚本三处输出的 canonical 字段命名完全一致

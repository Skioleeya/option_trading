## Why

当前 EOD 交易日标签把三类不同语义混在同一层里：

1. 路径结构：`trend_day`、`range_day`、`whipsaw_day`
2. 开盘上下文：`gap_trend_day`、`high_vol_open`
3. 事件/机制覆盖：`pinning_day`、`vol_crush_day`

这会导致 taxonomy 天然重叠。`gap_trend_day` 实际是 `trend_day + gap_open`，而拟议中的 `reversal_trend_day` 也会和 `reversal_day`、`trend_day` 重复表达同一日的不同维度。

学术文献更常见的做法不是为每种组合单独造一级标签，而是先定义可区分的市场状态或路径，再附加事件与上下文修饰符。基于该思路，本提案将交易日 taxonomy 改为“互斥主路径标签 + 正交修饰符”。

## What Changes

1. 引入互斥的 canonical `primary_day_type`：
   - `trend_day`
   - `reversal_day`
   - `balance_day`
   - `whipsaw_day`
2. 将非路径语义收敛为 `context_modifiers[]`，首批保留：
   - `gap_open`
   - `high_vol_open`
   - `pinning`
   - `vol_crush`
3. 引入 `close_profile`，用于表达收盘质量，而不是再造新的一级标签：
   - `strong_close`
   - `mid_close`
   - `weak_close`
4. 废止会造成重叠的一级组合标签设计：
   - `gap_trend_day` 改为 `trend_day + gap_open`
   - `pinning_day` 改为 `balance_day + pinning`
   - `vol_crush_day` 改为 `primary_day_type + vol_crush`
   - 禁止新增 `reversal_trend_day`
5. 规定实现阶段必须同步更新 cold manifest、quality report 与分类脚本输出合同，禁止只改其中一处。
6. 本提案采用硬切策略：旧 flat 标签字段与兼容输出在实施完成后必须从 active contract 中移除，不保留回退路径。

## Scope

- 目标：
  - `scripts/diagnostics/eod_bucket_*`
  - `data/cold/*` manifest / quality 输出合同
  - 研究与归档相关 SOP / OpenSpec 文档
- 非目标：
  - 本提案不直接修改运行时代码
  - 本提案不在本轮确定最终数值阈值
  - 本提案不要求立即重刷全部历史日归档

## Impact

- 研究标签将从“扁平互斥枚举”升级为“主标签 + 修饰符”
- 后续实现必须输出完整 canonical 字段：`primary_day_type`、`context_modifiers`、`close_profile`
- 后续实现完成后，active archive contract 中不得再出现 `primary_tag`、`legacy_primary_tag`、`matched_tags`
- 未来新增日型只能落在两类扩展点之一：
  - 新的主路径标签
  - 新的上下文修饰符

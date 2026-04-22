## Context

Wave1 目标是优先解决数据链断点与核心计算 owner 问题。先保证 L0 condition code 可达，再将关键判定公式迁入 Rust，最后在 MVP 层对齐字段输出。

## Design

1. L0 condition passthrough:
   - `ArrowMarketEvent` 增加 `trade_type/trade_session`
   - gateway trade 映射写入真实值
   - IPC schema 与 writer 同步新增列
2. Tick-rule:
   - 对 midpoint 成交优先使用 `prev_price` 判定
   - 若价格不变则沿用 `prev_direction`
3. MM Rust core:
   - `mm_tick_rule_direction`
   - `mm_condition_filtered`
   - `mm_oi_participation`
   - `mm_exposure_delta_gamma`
4. MVP output:
   - 实时 CSV 增加 Greeks exposure 与 condition/complex/tick-rule 指标

## Contract Consistency Check

本波结束前逐项核对：

1. OpenSpec `Field Contract` 列表
2. Rust schema / Python bridge dataclass 字段
3. CSV header 字段

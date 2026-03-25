## Design

### 1. Same-Day Anchor Self-Recovery

- 在 `AtmDecayTracker` 内部维护连续 `raw_pct_unavailable` 计数，只针对当前活动锚点的连续腿饥饿失效。
- 当失效次数达到阈值时，tracker 显式 `invalidate_anchor()`，并异步删除同交易日 persisted anchor，迫使后续 market-hour tick 走新的 ATM 锁定路径。
- 成功算出一笔有效 `raw_pct` 后立刻清零 streak，避免偶发单 tick 缺价触发误判。

### 2. Mandatory Symbol De-Pinning

- `housekeeping_loop` 对 anchor symbols 采用全量同步，不再只在非空时更新。
- 当锚点清空后显式下发空 mandatory-symbol set，确保旧锚点腿不会因为历史 mandatory 状态继续被钉住。

### 3. Operator Reset Path

- 允许盘中删除同日 ATM cold files 与 Redis anchor/history key，再重启 backend 触发一次干净的 same-day 重锁。
- 该操作不改 L3/L4 合同，只修复 L1/app 的锚点生存期管理。

### 4. Contract and Risk Notes

- `atm.timestamp` 继续表示样本事件时间，不改成广播时间。
- 不新增前端补丁或协议字段来掩盖后端锚点失活。
- persisted anchor 删除仅限当前 trade date，避免误伤历史日数据。

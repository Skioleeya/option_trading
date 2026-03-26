## Design

### L3 Payload Debug

在 compute loop 组装完成 `FrozenPayload` 后，追加统一摘要日志：

- marker: `[L3-PAYLOAD]`
- fields:
  - `tick_id`
  - `snapshot_version`
  - `duplicate`
  - `depth_rows`
  - `depth_spot`
  - `depth_flip`
  - `depth_put_peak` / `depth_put_pct`
  - `depth_call_peak` / `depth_call_pct`
  - `atm_status`
  - `atm_ts`
  - `atm_straddle`
  - `atm_call`
  - `atm_put`

duplicate snapshot 路径只按节流规则打印，避免 1Hz 无意义刷屏。

### ATM Status Semantics

- `LIVE`: payload 中存在 `atm`
- `MISSING_OUTSIDE_RTH`: 当前 ET 不在 09:30-16:00，tracker 按设计返回 `None`
- `MISSING`: 处于 regular hours，但仍未得到 `atm` payload，需要继续排障

### L4 History Hydrate Debug

`App.tsx` 在 `/api/atm-decay/history` 冷启动拉取成功后打印一次：

- rows count
- last timestamp
- last `straddle/call/put`

用于确认 TradingView 图表的数据来源至少已经到浏览器侧。

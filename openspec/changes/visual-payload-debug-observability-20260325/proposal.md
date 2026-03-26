## Why

联查显示两个不同现象需要被明确区分：

1. `DepthProfile` live contract 在 L3/L4 是有效传输的。
2. `TradingView` 的 `call/put/straddle` live `atm` payload 在盘后为空，不是 transport 丢包，而是 ATM tracker 的 regular-hours gate 主动返回 `None`。

现有日志缺少一个统一的 payload 级可视化摘要，导致只能靠抓 websocket 帧手工推断。

## What Changes

1. 增加统一的 `[L3-PAYLOAD]` 结构化日志，显式总结：
   - `depth_profile` 行数、spot/flip/peak strikes
   - `atm` 状态、时间戳、`straddle/call/put` 百分比
2. 在 L4 cold-boot history hydrate 成功时输出一次 `[L4 ATM]` 日志，明确 TradingView 曲线拿到了多少历史点。

## Impact

- 不改变现有 UI payload contract。
- 提升盘中/盘后对 `DepthProfile` 与 ATM chart 链路的可观测性。
- 明确区分 `live atm missing because outside RTH` 和 `transport missing`.

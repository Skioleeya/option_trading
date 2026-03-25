## Design Summary

采用“L1 tracker 内聚 replay + 标准 API/WS 复用”的设计：

1. `AtmDecayReplayService` 只在 after-hours 且显式配置开启时激活。
2. Replay 从冷存储选择同时具备 `atm_<date>.json` 与 `atm_series_<date>.jsonl` 的历史交易日。
3. Replay 仅选择非 flat、首尾非 `0/0/0` 的窗口，并重映射到今天的 ET 交易日。
4. `AtmDecayTracker` 负责把 replay anchor/history 写入今天标准存储，并在 `update()` 返回 replay tick。

## Boundary Contract

- 允许：`tracker -> replay service -> storage`
- 禁止：`app` 直接访问 tracker/storage 私有成员
- 保持：L3/L4 仍通过既有 `atm` payload 与 `/api/atm-decay/history` 消费数据

## Data Contract

新增测试配置：

- `ATM_DECAY_REPLAY_ENABLED`
- `ATM_DECAY_REPLAY_SOURCE_DATE`
- `ATM_DECAY_REPLAY_WINDOW_SECONDS`
- `ATM_DECAY_REPLAY_STEP_SECONDS`

公开行为变化：

- 盘后测试态下，`AtmDecayTracker.update()` 可返回 replay tick
- `/api/atm-decay/history` 仍返回 today 的标准 history
- `/ws/dashboard` 仍发送原合同 `atm` 字段，无 replay-only wire schema

## Validation Plan

- 单测：source 选择、窗口筛选、时间重映射、tracker after-hours replay
- 端到端：60s API/WS/TradingView 验证，要求 history 非空、曲线非平台化、浏览器 canvas 正常
- Strict：session validation、quality gate、openspec chain gate

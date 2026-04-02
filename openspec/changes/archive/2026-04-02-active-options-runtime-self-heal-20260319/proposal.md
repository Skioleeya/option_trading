## Why

`ActiveOptions` 在连接抖动期间会长期降级为占位行，根因是 L0 Rust REST 路径在运行中失败后无法自动切端点并恢复会话。

## What Changes

- 增强 `RustQuoteRuntime` 运行中 failover：支持 `stop -> 切端点 -> 重建 -> 重订阅`，并限制为单次切换+单次重试。
- 增加 failover 诊断字段，透出到 `/debug/persistence_status`。
- 增加 ActiveOptions 空过滤诊断（计数/时间/占位状态），便于前后端统一定位。
- 增加 ActiveOptions 行质量标记：`row_quality / fallback_reason / is_synthetic_fallback`（向后兼容）。
- 修复 L0 flow 字段污染：`DEPTH` 事件不再写入 `volume/current_volume/turnover`，`ws_*_seen` 改为正值语义。
- 增加 degraded + `FLOW_ACTIVE_MIN_VOLUME=10` 热修启动入口与一次性验活脚本。

## Outcome

连接失败时系统可自愈恢复，ActiveOptions 不再长期空榜；同时具备明确线上证据链用于判因与回归。

## Why

Active Options 在链路有成交量时仍长期出现 `missing_turnover` 降级，根因是 Rust SHM push 事件未向 Python 桥接输出 `turnover/current_volume`。

## What Changes

- 将 SHM 事件升级为 v2：在尾部追加 `current_volume/turnover/current_turnover`。
- 在 SHM 头部保留区写入 `magic/schema_version/event_size` 握手元数据。
- Python `RustBridge` 引入布局注册器，支持 v2 优先 + v1 兼容解包。
- `parse_rust_event` 映射 `current_volume/turnover` 到 `CleanQuoteEvent`。
- 同步字典与 SOP，明确 owner/fallback/diagnostics 契约。

## Outcome

在 push quote 可用时，`ws_turnover_seen` 可增长，Active Options 不再因链路缺字段长期全量 `missing_turnover`。

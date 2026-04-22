# Open Tasks

## Priority Queue
- [ ] P2: 在更高波动真实市场窗口复采 `SPY.US` distinct midpoint cadence，确认业务上的“实时感”是否满足；该项是监测，不是当前 root-fix 的阻塞项。(owner: Codex, due: 2026-04-26)

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 将 `SPY.US` 纳入正式 live subscribe 集合，cap trim 不得移除 (2026-04-21 12:34 ET)
- [x] 删除运行中 REST `quote(["SPY.US"])` spot fallback，保留 startup bootstrap only (2026-04-21 12:34 ET)
- [x] 将 SPY live spot owner 从 `last_done` 改为 live depth midpoint (2026-04-21 12:47 ET)
- [x] 修复 `RustQuoteRuntime.subscribe()` 假 reconcile，真实下发 add/remove 到 Rust gateway (2026-04-21 12:48 ET)
- [x] 重编并替换运行时 `l0_rust.so` 工件，real-host 重启验证通过 (2026-04-21 12:53 ET)
- [x] 采集 real-host `store.spot` vs websocket `spot` 同窗样本，确认 L4 已重新收到 `spot` delta (2026-04-21 12:58 ET)
- [x] 采集 `L3 Assembler spot/version` vs websocket `spot/version` 同窗样本，确认 websocket 不丢 `spot/version`，剩余延迟来自调度相位 (2026-04-21 13:38 ET)
- [x] 将 `broadcast_loop` 改为 payload-triggered + heartbeat fallback，并用 real-host `trigger=payload age=0ms` 日志确认整秒级相位等待已消除 (2026-04-21 13:47 ET)
- [x] 为 `SPY` 增加 live spot fast lane：L0 `update_spot()` 事件直接 overlay 当前 wire payload，top-level `spot/version` 不再受 1Hz compute cadence 限制 (2026-04-21 14:12 ET)
- [x] 为 `SPY` quote lane 补齐 source/transport/render 观测链：L0 cadence diagnostics -> L3 `governor_telemetry.quote_lane` -> L4 RUM/DebugOverlay (2026-04-21 14:36 ET)
- [x] 用真实浏览器 CDP 采到 `quote_lane + L4Rum` 同窗样本，并修复 live-spot overlay 覆盖 cadence 字段的问题 (2026-04-21 14:52 ET)
- [x] 为 `quote_lane` 拆开 raw source cadence 与 distinct midpoint cadence；确认当 L0 收到新 source tick 时，L3/L4 已低延迟对齐 (2026-04-21 15:03 ET)
- [x] 为 Rust gateway 增加 `SPY.US` raw quote/depth push telemetry，证明 Longbridge raw `DEPTH` cadence 约 `3-4/s`，问题不在 broker 原始推送 (2026-04-21 15:18 ET)
- [x] 100% 定责 `raw DEPTH -> midpoint accepted` 丢失根因：Arrow IPC 单槽 latest-message 覆盖，而不是 one-sided/crossed/字段缺失 (2026-04-21 15:34 ET)
- [x] 将 Arrow IPC 从单槽覆盖改为多槽有序队列，reader 引入本地 cursor 顺序 drain，transport diagnostics 暴露 `writer_batch_id/reader_last_batch_id/queued/dropped/gaps` (2026-04-21 15:42 ET)
- [x] real-host 六个连续样本确认 transport root-fix 生效：`raw_depth_event_count_1s` 与 `source_event_count_1s` 对齐到 `3-4/s`，且 `queued=0 dropped=0 gaps=0` (2026-04-21 15:44 ET)

# Open Tasks

## Priority Queue
- [ ] P1: 将 Rust batch/shm runtime 参数从 env override 继续收敛到更明确的 config/bridge owner
  - Owner: Codex
  - Definition of Done: 不再由 Rust runtime 局部自行定义 batch/shm env key 语义
  - Blocking: 需要明确跨 Python/Rust 配置桥接方案
- [ ] P1: 评估 `openapi_bootstrap.py` / `quote_runtime.py` 的 env write 是否继续下沉为更窄的 SDK adapter
  - Owner: Codex
  - Definition of Done: endpoint alias propagation 不再散落在 source runtime
  - Blocking: 需要确认 LongPort SDK 仍必须依赖环境变量
- [ ] P2: 为 Rust transport owner 增加原生单元测试
  - Owner: Codex
  - Definition of Done: `resolve_arrow_signal_name` 与 env-key 常量在 Rust 侧有独立测试
  - Blocking: 需要补充 `cargo test` 覆盖范围

## Parking Lot
- [ ] 将 Python/Rust transport constants 生成化，避免双边人工镜像
- [ ] 为 L0 transport owner 补充 SOP/architecture note

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] `MarketDataGateway` direct env reads 已收敛到 `shared.config.settings` (2026-04-01 11:48 ET)
- [x] Rust `ipc_writer` signal owner 已改为 dedicated transport contract module (2026-04-01 11:48 ET)

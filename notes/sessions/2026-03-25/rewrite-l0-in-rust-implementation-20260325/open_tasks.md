# Open Tasks

## Priority Queue
- [x] P0: 将 L0 Rust 热路径切到 Arrow IPC producer，并让 legacy SHM producer 退出热路径
  - Owner: Codex
  - Definition of Done: `gateway_core.rs` 使用 Arrow batch writer、`SubFlags` 收敛为 `QUOTE|DEPTH|TRADE`、legacy `IpcProducer` 仅保留兼容双写守卫
  - Blocking: 已完成
- [x] P1: 建立“L0 层无 Python 文件”的迁移边界并开始剥离活跃接线
  - Owner: Codex
  - Definition of Done: `app/container.py` 不再依赖 `l0_ingest.v2`，活跃 Python runtime 已整体迁移到 `shared/services/l0_runtime`
  - Blocking: 已完成
- [x] P2: 同步测试、SOP、OpenSpec/session 文档并跑 strict validation
  - Owner: Codex
  - Definition of Done: 相关回归、`scripts/validate_session.ps1 -Strict`、quality gate、openspec chain gate 全绿
  - Blocking: 已完成

## Parking Lot
- [x] Windows 平台 Arrow IPC signal 合同已落地：Rust `windows_signal.rs` 与 Python `shared/system/ipc_signal.py` 已按 `L0_IPC_SIGNAL_NAME` create-or-open named event 对齐
- [ ] 将 `shared/services/l0_runtime` 活跃消费面切到 `ArrowIpcReader` / Arrow IPC 批次读取
- [ ] 在消费面切换与回归通过后，退场 Rust legacy SHM 兼容双写
- [x] `l0_ingest` 下 Python 文件已清零；剩余迁移面只剩消费切换与旧 SHM 双写退场

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] 重跑 `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`，确认 session/context/SOP/OpenSpec 同步后仍全绿 (2026-03-25 15:07 ET)
- [x] 补记并固化“Windows named-event signal 已完成；剩余只剩消费面切换/legacy 双写退场”的 session/context/SOP/OpenSpec 记录 (2026-03-25 15:03 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` 通过，architecture/quality/openspec/debt gate 全绿 (2026-03-25 14:49 ET)
- [x] 将 `l0_ingest` 下剩余 support/shim/test Python 整体迁出到 `shared/services/l0_support`、`shared/services/l0_runtime` 与顶层 `tests/`，实现 `l0_ingest` 下 0 个 `.py` 文件 (2026-03-25 14:48 ET)
- [x] `scripts/test/run_pytest.ps1 tests/l0_support tests/l0_runtime` 全量 125 项通过，确认迁移后 legacy/support/runtime 三条 Python 路径保持可用 (2026-03-25 14:49 ET)
- [x] 将 `l0_ingest/v2` 活跃 Python runtime 整体迁移到 `shared/services/l0_runtime`，并切断 `app/container.py -> l0_ingest.v2` 依赖 (2026-03-25 14:39 ET)
- [x] `scripts/test/run_pytest.ps1 l0_ingest/tests/v2` 全量 73 项通过，确认迁移后导入与行为未回归 (2026-03-25 14:41 ET)
- [x] 在 Rust crate 内新增 `ipc_writer.rs`、`ARROW_IPC_SCHEMA`、Arrow IPC SHM writer，并保留 legacy SHM 兼容双写 (2026-03-25 14:29 ET)
- [x] `cargo test` 通过，确认新的 Rust writer/网关改动可编译 (2026-03-25 14:30 ET)
- [x] `scripts/test/run_pytest.ps1 l0_ingest/tests/v2/test_quote_runtime.py` 通过，确认 Python runtime 调用面未被破坏 (2026-03-25 14:31 ET)
- [x] 重读 `rewrite-l0-in-rust` proposal/design/tasks/spec，并纳入新增 SDK 合规要求 (2026-03-25 14:16 ET)
- [x] 创建实现 session 并切换 context active pointer (2026-03-25 14:14 ET)
- [x] 完成 L0 Python 文件与跨层导入基线扫描，确认硬切范围 (2026-03-25 14:23 ET)

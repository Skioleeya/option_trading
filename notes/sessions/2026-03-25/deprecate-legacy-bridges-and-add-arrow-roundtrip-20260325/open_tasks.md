# Open Tasks

## Priority Queue
- [x] P0: 为 `shared/system/rust_shm_bridge.py` 与 legacy `rust_event_bridge` 增加显式 deprecate 标记
  - Owner: Codex
  - Definition of Done: live path 不再从 deprecated module 引用 active 实现；compat wrapper 在导入/构造时显式发出 `DeprecationWarning`
  - Blocking: 已完成
- [x] P1: 新增 `tests/l0_runtime/test_arrow_roundtrip.py`
  - Owner: Codex
  - Definition of Done: Rust producer 与 Python `ArrowIpcReader` 在 Windows named-event contract 下完成真实 batch roundtrip 验证
  - Blocking: 已完成
- [x] P1: 同步 SOP/OpenSpec/session/context 并跑 strict validation
  - Owner: Codex
  - Definition of Done: 会话、上下文、SOP、OpenSpec 与验证结果一致，`scripts/validate_session.ps1 -Strict` 全绿
  - Blocking: 已完成

## Parking Lot
- [ ] 若后续需要多 batch 顺序消费，补独立 batch queue/sequence contract；当前共享段仍是“最新 batch 覆盖”模型

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] `tests/l0_runtime/test_rust_event_bridge.py tests/l0_runtime/test_option_chain_builder_rust_events.py tests/l0_runtime/test_arrow_ipc_signal.py tests/l0_runtime/test_arrow_roundtrip.py` 共 10 项通过 (2026-03-25 16:02 ET)
- [x] `cargo test` 通过，新增 `arrow_ipc_segment_exposes_named_mapping` 单测验证 Rust named mapping 可回开 (2026-03-25 16:10 ET)
- [x] Rust 兼容壳已从 `ipc.rs` 重命名为 `ipc_legacy.rs`，OpenSpec 最后一项清理任务完成 (2026-03-25 16:24 ET)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` 全绿通过 (2026-03-25 16:19 ET)
- [x] `rust_event_bridge.py` 退化为 deprecated compatibility wrapper，active normalize path 移到 `market_event_bridge.py` (2026-03-25 15:31 ET)
- [x] `rust_shm_bridge.py` 明确标记为 deprecated compatibility bridge，不再允许误接回 `rust_only` live path (2026-03-25 15:31 ET)
- [x] `tests/l0_runtime/test_arrow_roundtrip.py` 覆盖 Rust producer -> Python Arrow reader 的 live batch roundtrip (2026-03-25 16:00 ET)

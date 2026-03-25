# Open Tasks

## Priority Queue
- [x] P0: 将 `shared/services/l0_runtime` 活跃消费面从 legacy SHM polling 切到 `ArrowIpcReader`
  - Owner: Codex
  - Definition of Done: `rust_only` 不再接线 `RustBridge.poll()`；`OptionChainBuilder` 改为消费 Arrow batch；`fetch_snapshot` 诊断合同继续稳定输出
  - Blocking: 已完成
- [x] P1: 让 Rust L0 热路径退场 legacy SHM dual-write
  - Owner: Codex
  - Definition of Done: `gateway_core.rs` 不再在 hot path 调用 `IpcProducer.push(...)`，Arrow IPC 成为唯一实时推送输出
  - Blocking: 已完成
- [x] P2: 同步 SOP/OpenSpec/session/context 并跑 strict validation
  - Owner: Codex
  - Definition of Done: 文档与会话台账写明 consumer cutover/dual-write retirement 已完成，`scripts/validate_session.ps1 -Strict` 全绿
  - Blocking: 已完成

## Parking Lot
- [x] 为 `shared/system/rust_shm_bridge.py` 与 legacy `rust_event_bridge` 增加显式 deprecate 标记，避免下轮误接回 live path (COMPLETED-IN: `2026-03-25/deprecate-legacy-bridges-and-add-arrow-roundtrip-20260325`)
- [x] 增加 `tests/l0_runtime/test_arrow_roundtrip.py`，覆盖 Rust producer -> Python reader 的 batch roundtrip 集成验证 (COMPLETED-IN: `2026-03-25/deprecate-legacy-bridges-and-add-arrow-roundtrip-20260325`)

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` 通过，session/context/SOP/OpenSpec 同步后全绿 (2026-03-25 15:25 ET)
- [x] Rust hot path 移除 legacy SHM dual-write，Arrow IPC 成为唯一实时输出 (2026-03-25 15:18 ET)
- [x] `OptionChainBuilder` 在 `rust_only` 模式下切到 `ArrowIpcReader` 消费 Arrow batch，`python_fallback` 保留 `event_queue` (2026-03-25 15:16 ET)
- [x] `cargo test` 通过，确认 Rust gateway/IPC 改动编译与单测正常 (2026-03-25 15:17 ET)
- [x] `scripts/test/run_pytest.ps1 tests/l0_runtime/test_arrow_ipc_signal.py tests/l0_runtime/test_fetch_chain_components.py tests/l0_runtime/test_quote_runtime.py tests/l0_runtime/test_option_chain_builder_rust_events.py` 全量 17 项通过 (2026-03-25 15:17 ET)
- [x] `scripts/test/run_pytest.ps1 tests/l0_runtime app/tests/test_health_route_diagnostics.py app/tests/test_compute_loop_timestamp.py app/loops/tests/test_compute_loop_gpu_dedup.py app/loops/tests/test_compute_loop_atm_live_continuity.py` 全量 84 项通过 (2026-03-25 15:19 ET)
- [x] 更新 SOP/OpenSpec，固化 Arrow consumer cutover、`batch_id` 诊断语义与 legacy dual-write 退场记录 (2026-03-25 15:20 ET)

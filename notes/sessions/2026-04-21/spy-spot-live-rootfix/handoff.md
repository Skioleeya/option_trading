# Handoff

## Session Summary
- DateTime (ET): 2026-04-21 15:45:49 -04:00
- Goal: 修复 `SPY.US` raw `DEPTH` 在 `raw DEPTH -> midpoint accepted` 链路上的真实丢失根因，并证明 L0 -> L3 -> L4 已恢复为低延迟、无 transport 丢批次传递。
- Outcome: 根因已修复。`SPY.US` 现继续以 live depth midpoint 作为唯一 spot owner，但 Arrow IPC transport 已从单槽 latest-message 覆盖切为多槽有序队列，reader 通过本地 cursor 顺序 drain backlog；real-host 连续样本确认 `raw_depth_event_count_1s` 与 Python `source_event_count_1s` 已对齐到 `3-4/s`，且 `queued_batch_count=0`、`dropped_batch_count=0`、`reader_gap_count=0`。因此之前的 source cadence 缺口已被定责并关闭，remaining cadence 仅由真实 midpoint 变化本身决定，而非 transport 丢失。

## What Changed
- Code / Docs Files:
  - `l0_ingest/l0_rust/src/arrow_ipc.rs`
  - `l0_ingest/l0_rust/src/arrow_ipc_tests.rs`
  - `l0_ingest/l0_rust/src/ipc_runtime.rs`
  - `l0_ingest/l0_rust/src/ipc_writer.rs`
  - `l0_ingest/l0_rust/src/lib.rs`
  - `shared/services/l0_runtime/source/runtime/ipc.py`
  - `shared/services/l0_runtime/services/runtime/builder.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `notes/sessions/2026-04-21/spy-spot-live-rootfix/project_state.md`
  - `notes/sessions/2026-04-21/spy-spot-live-rootfix/open_tasks.md`
  - `notes/sessions/2026-04-21/spy-spot-live-rootfix/handoff.md`
  - `notes/sessions/2026-04-21/spy-spot-live-rootfix/meta.yaml`
- Runtime / Infra Changes:
  - Arrow IPC transport 不再是共享内存单 payload 槽位；writer 现在按 batch 序号写入多槽队列，reader 按本地 cursor 顺序读取，不再通过覆盖最新 payload 丢掉中间 batch。
  - `NativeArrowIpcReader` 新增 transport diagnostics：`writer_batch_id`、`reader_last_batch_id`、`queued_batch_count`、`dropped_batch_count`、`reader_gap_count`。
  - Python `ArrowIpcReader` 新增 `transport_diagnostics()`，`OptionChainBuilderV2` 已把 transport 指标并入 `/debug/persistence_status -> stores.transport`，并把 `shm_stats.head/tail` 对齐为 writer/reader batch id。
  - Rust reader cursor 现由内部 `Mutex<ArrowIpcReadCursor>` 持有，避免 live diagnostics 与 batch 读取并发时触发 `Already mutably borrowed`。
  - `docs/SOP/L0_DATA_FEED.md` 已同步 Arrow IPC contract：语义从单槽 latest-message 覆盖改为多槽有序队列，diagnostics contract 同步更新。

## Commands Run
- `cargo test --manifest-path l0_ingest/l0_rust/Cargo.toml`
- `.venv/bin/python manage.py run-pytest shared/services/l0_runtime/source/runtime/test_quote_runtime.py app/tests/test_health_route_diagnostics.py app/loops/tests/test_compute_loop_atm_live_continuity.py`
- `cargo build --release --manifest-path l0_ingest/l0_rust/Cargo.toml --target-dir tmp/cargo_target_runtime_l0`
- `cp tmp/cargo_target_runtime_l0/release/libl0_rust.so shared/services/l0_runtime/_native_generated/l0_rust.so`
- `cp tmp/cargo_target_runtime_l0/release/libl0_rust.so shared/services/l0_runtime/_native_generated/wave10/l0_rust.so`
- `python3 manage.py start-all`
- `.venv/bin/python - <<'PY' ... sample /debug/persistence_status six times and compare stores.gateway raw_* with stores.store.quote_lane and stores.transport ... PY`
- `python3 manage.py validate-session --strict`

## Verification
- Passed:
  - `cargo test --manifest-path l0_ingest/l0_rust/Cargo.toml` (`4 passed`)
  - `.venv/bin/python manage.py run-pytest shared/services/l0_runtime/source/runtime/test_quote_runtime.py app/tests/test_health_route_diagnostics.py app/loops/tests/test_compute_loop_atm_live_continuity.py` (`6 passed`)
  - `cargo build --release --manifest-path l0_ingest/l0_rust/Cargo.toml --target-dir tmp/cargo_target_runtime_l0`
  - `python3 manage.py start-all` (`Redis 6380 True / Backend 8001 True / Frontend 5173 True`)
  - real-host six-sample `/debug/persistence_status` check:
    - `stores.gateway.raw_depth_event_count_1s = 3-4`
    - `stores.store.quote_lane.source_event_count_1s = 3-4`
    - `stores.transport.writer_batch_id == stores.transport.reader_last_batch_id`
    - `stores.transport.queued_batch_count = 0`
    - `stores.transport.dropped_batch_count = 0`
    - `stores.transport.reader_gap_count = 0`
    - conclusion: transport no longer drops SPY depth batches
  - `python3 manage.py validate-session --strict` (`PASS`; quality gate `PASS`, openspec gate `PASS`, final line `Session validation passed.`)
- Failed / Not Run:
  - First live deploy after the queue cutover briefly failed `/debug/persistence_status` with `Already mutably borrowed`; this was fixed by moving the Rust reader cursor behind `Mutex<ArrowIpcReadCursor>` and rerunning the build + deploy.

## Pending
- Must Do Next:
  - None for this root fix.
- Nice to Have:
  - 在更高波动真实市场窗口复采 `SPY.US` distinct midpoint cadence，确认业务上的“实时感”是否满足；这是监测项，不是当前 transport root-fix 的未完事项。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本次 root cause 已在同 session 内完成实现、部署、real-host 验证和 strict 校验，无残留兼容层或临时 wrapper 债务。
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-21
- DEBT-RISK: Low；剩余仅为业务侧对真实 midpoint 变化频率的观察，不是系统性 transport 缺陷。
- DEBT-NEW: 0
- DEBT-CLOSED: 1
- DEBT-DELTA: -1
- RUNTIME-ARTIFACT-EXEMPT: 已重编并替换 `shared/services/l0_runtime/_native_generated/l0_rust.so` 与 `wave10/l0_rust.so`；二进制工件不纳入 `files_changed`。

## Exemptions
- OPENSPEC-EXEMPT: 本次为 L0 transport root-cause fix，不变更外部 API、schema 或跨层合同。
- SOP-UPDATED: `docs/SOP/L0_DATA_FEED.md`

## How To Continue
- Start Command:
  - `python3 manage.py start-all`
- Key Logs:
  - `logs/backend_runtime.current.log`
  - `logs/frontend_runtime.current.log`
- First File To Read:
  - `l0_ingest/l0_rust/src/arrow_ipc.rs`

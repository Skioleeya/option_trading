# Handoff

## Session Summary
- DateTime (ET): 2026-03-19 16:32:00 -04:00
- Goal: 修复 `quote_runtime -> rust bridge` 丢失 `turnover/current_volume`，并保持下游 store/fetch 透传逻辑不变。
- Outcome: 已实现 SHM v2 字段+头部握手、Python v1/v2 兼容解包、L0 rust_event 映射修复；并补上 L0 负 volume 防护 + WS 双体积字段融合修复（单字段脏值不再污染 Active Options）。

## What Changed
- Code / Docs Files:
  - `l0_ingest/l0_rust/src/schema.rs`
  - `l0_ingest/l0_rust/src/ipc.rs`
  - `l0_ingest/l0_rust/src/lib.rs`
  - `l1_compute/rust_bridge.py`
  - `l0_ingest/feeds/rust_event_bridge.py`
  - `l0_ingest/feeds/chain_state_store.py`
  - `l1_compute/tests/test_rust_bridge.py`
  - `l0_ingest/tests/test_rust_event_bridge.py`
  - `l0_ingest/tests/test_option_chain_builder_rust_events.py`
  - `l0_ingest/tests/test_chain_state_store.py`
  - `docs/LONGPORT_OPTION_FIELD_DICTIONARY.md`
  - `docs/SOP/L0_DATA_FEED.md`
  - `openspec/changes/turnover-shm-v2-handshake-20260319/*`
- Runtime / Infra Changes:
  - SHM 事件契约升级到 v2（尾部新增 `current_volume/turnover/current_turnover`）
  - SHM 头部新增握手元数据（`magic/schema_version/event_size`）
  - Python bridge 在 metadata 缺失时自动回退 v1 解包
  - Rust quote push 恢复独立透传：`volume=q.volume`、`current_volume=q.current_volume`
  - ChainStateStore 增加 WS volume 融合策略：两字段都有效时取较小值，单字段损坏时自动退避
- Commands Run:
  - `./scripts/test/run_pytest.ps1 l1_compute/tests/test_rust_bridge.py l0_ingest/tests/test_rust_event_bridge.py l0_ingest/tests/test_option_chain_builder_rust_events.py`
  - `./scripts/test/run_pytest.ps1 l0_ingest/tests/test_chain_state_store.py`
  - `./scripts/test/run_pytest.ps1 l0_ingest/tests/test_chain_state_store.py`（第二轮：11 passed）
  - `cargo test` (workdir: `l0_ingest/l0_rust`)
  - `./scripts/ops/verify_active_options_hotfix.ps1`（operator，最新一次 PASS）
  - `./scripts/ops/verify_active_options_hotfix.ps1`（operator）
  - `/debug/persistence_status` 1Hz 监控循环（operator）

## Verification
- Passed:
  - 定向 pytest: `l0_ingest/tests/test_chain_state_store.py` -> 11 passed
  - 定向 pytest: 10 passed
  - `./scripts/validate_session.ps1 -Strict`: PASS（quality/openspec/debt/context 全绿）
  - 在线验活（2026-03-19 15:09 ET）:
    - `curl http://127.0.0.1:8001/health` -> `{"status":"ok",...}`
    - `./scripts/ops/verify_active_options_hotfix.ps1` -> `PASS`
    - 关键指标: `live_rows=3`, `degraded_rows=2`, `missing_turnover_rows=0`
  - 在线验活（2026-03-19 15:35 ET）:
    - `./scripts/ops/verify_active_options_hotfix.ps1` -> `PASS`
    - 关键指标: `chain_size=260`, `live_rows=4`, `degraded_rows=1`, `missing_gamma_rows=1`, `missing_turnover_rows=0`
  - 连续监控（15:09:58-15:10:15 ET）:
    - `live=4 degraded=1 missing_turnover=0 ws_turnover_seen=52`
    - `chain_size` 从 `231` 增长到 `259`
- Failed / Not Run:
  - Rust `cargo test`: 失败（`link.exe` not found，MSVC 工具链缺失）

## Pending
- Must Do Next:
  - 无（本次交付目标已完成并验活通过）
- Nice to Have:
  - 在具备 MSVC 环境后补跑 Rust 编译/测试并记录证据

## Debt Record (Mandatory)
- DEBT-EXEMPT: Rust 编译环境缺失（`link.exe`）导致本地 `cargo test` 无法完成
- DEBT-OWNER: User
- DEBT-DUE: 2026-03-19
- DEBT-RISK: 无法在本机完成 Rust 编译回归，存在环境相关回归盲区
- DEBT-NEW: 1
- DEBT-CLOSED: 0
- DEBT-DELTA: 1
- DEBT-JUSTIFICATION: 受本机工具链限制，已以 Python 层与桥接层单测覆盖主要行为路径
- RUNTIME-ARTIFACT-EXEMPT: N/A

## How To Continue
- Start Command: `./scripts/ops/start_backend.ps1`
- Key Logs: `[RustBridge] SHM metadata`, `[OptionChainBuilder]`, `missing_turnover_rows/live_rows`
- First File To Read: `l1_compute/rust_bridge.py`

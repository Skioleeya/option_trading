# Handoff

## Session Summary
- DateTime (ET): 2026-03-19 16:49:15 -04:00
- Goal: 消除 Active Options 中超大 `volume` 脏值穿透，恢复排行稳定性并避免 `missing_gamma` 误退化。
- Outcome: 已完成 L0 入口防污染 + shared 归一化兜底 + 验活脚本口径修正；定向回归全绿。在线验活受环境进程限制未完成。

## What Changed
- Code / Docs Files:
  - `l0_ingest/feeds/chain_state_store.py`
  - `l0_ingest/tests/test_chain_state_store.py`
  - `shared/services/active_options/runtime_service_support.py`
  - `shared/services/active_options/test_runtime_service.py`
  - `scripts/ops/verify_active_options_hotfix.ps1`
  - `docs/SOP/L0_DATA_FEED.md`
- Runtime / Infra Changes:
  - WS `volume/current_volume` 引入 hard cap（`1_000_000_000`）清洗；超限值丢弃且不置位 WS owner。
  - 新增 `ws_volume_dropped/ws_current_volume_dropped` 诊断计数。
  - Active Options normalize 增加同口径体积清洗，阻断上游任一路径脏值穿透。
  - 验活脚本门禁从 `live_rows` 改为 `real_rows + missing_turnover`，兼容收盘降级场景。
- Commands Run:
  - `./scripts/new_session.ps1 -TaskId active-options-volume-sanitize-20260319 -Title "Active options volume sanitize hardening" -Scope "l0_ingest,shared,scripts,docs" -Owner "Codex" -UpdatePointer`
  - `./scripts/test/run_pytest.ps1 l0_ingest/tests/test_chain_state_store.py -k "corruption_with_turnover"`
  - `./scripts/test/run_pytest.ps1 l0_ingest/tests/test_chain_state_store.py shared/services/active_options/test_runtime_service.py`
  - `./scripts/test/run_pytest.ps1 l0_ingest/tests/test_rust_event_bridge.py l0_ingest/tests/test_option_chain_builder_rust_events.py l1_compute/tests/test_rust_bridge.py`
  - `./scripts/validate_session.ps1 -Strict`（PASS）
  - `./scripts/ops/start_backend.ps1 -HotfixActiveOptions`（失败：`Start-Process` 子进程限制）
  - `./scripts/ops/verify_active_options_hotfix.ps1`（失败：backend 未启动）

## Verification
- Passed:
  - `./scripts/test/run_pytest.ps1 l0_ingest/tests/test_chain_state_store.py shared/services/active_options/test_runtime_service.py` -> 35 passed
  - `./scripts/test/run_pytest.ps1 l0_ingest/tests/test_rust_event_bridge.py l0_ingest/tests/test_option_chain_builder_rust_events.py l1_compute/tests/test_rust_bridge.py` -> 10 passed
  - `./scripts/validate_session.ps1 -Strict` -> PASS
- Failed / Not Run:
  - 在线验活未完成：`start_backend.ps1` 在当前环境无法创建子进程（`cmd.exe` 启动报“找不到指定的模块”）
  - `./scripts/ops/verify_active_options_hotfix.ps1` 因 backend 不可达失败

## Pending
- Must Do Next:
  - 在可启动 backend 的环境执行 `./scripts/ops/start_backend.ps1 -HotfixActiveOptions` 后复跑 `./scripts/ops/verify_active_options_hotfix.ps1`
  - 用 `/history?view=full&count=1` 二次确认 active options 行不再出现超大 `volume`
- Nice to Have:
  - 增加 Rust/L0 原始字段采样日志，继续追踪上游脏值源头（WS 原始字段或 SHM 并发写竞态）
  - OPENSPEC-EXEMPT: 本轮为脏值防护硬化与验活口径修订，未引入新业务契约或跨层接口变更

## Debt Record (Mandatory)
- DEBT-EXEMPT: 当前环境无法启动 backend 进程，在线验活证据缺失
- DEBT-OWNER: User
- DEBT-DUE: 2026-03-19
- DEBT-RISK: 仅有离线单测证据，缺少实时行情链路最终确认
- DEBT-NEW: 1
- DEBT-CLOSED: 0
- DEBT-DELTA: 1
- DEBT-JUSTIFICATION: 受运行环境子进程启动限制，无法完成本机在线验活
- RUNTIME-ARTIFACT-EXEMPT: backend process launch blocked by host runtime restriction

## How To Continue
- Start Command: `./scripts/ops/start_backend.ps1 -HotfixActiveOptions`
- Key Logs: `[ChainStateStore] dropped implausible WS volume`, `ws_volume_dropped/ws_current_volume_dropped`, `[verify-hotfix]`
- First File To Read: `l0_ingest/feeds/chain_state_store.py`

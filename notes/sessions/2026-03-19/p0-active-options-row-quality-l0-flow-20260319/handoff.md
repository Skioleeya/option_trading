# Handoff

## Session Summary
- DateTime (ET): 2026-03-19 13:12:17 -04:00
- Goal: 按 P0 计划修复 ActiveOptions “伪真实静态行”并升级质量门禁，禁止合成行冒充真实可交易行。
- Outcome: 已完成根因修复与契约升级；单测/回归与 strict 全通过；本 shell 在线验活受 `WinError 10106` 限制。

## What Changed
- Code / Docs Files:
  - `l0_ingest/feeds/chain_state_store.py`
  - `l0_ingest/tests/test_chain_state_store.py`
  - `shared/services/active_options/runtime_service_support.py`
  - `shared/services/active_options/runtime_service.py`
  - `shared/services/active_options/test_runtime_service.py`
  - `l3_assembly/events/payload_events.py`
  - `l3_assembly/events/active_options_contract.py`
  - `l4_ui/src/types/dashboard.ts`
  - `scripts/ops/verify_active_options_hotfix.ps1`
  - `scripts/diag/check_active_options_no_data_cause.py`
  - `app/tests/test_health_route_diagnostics.py`
  - `docs/SOP/L0_DATA_FEED.md`
  - `openspec/changes/active-options-runtime-self-heal-20260319/proposal.md`
  - `openspec/changes/active-options-runtime-self-heal-20260319/specs/l0-runtime-resilience/spec.md`
  - `openspec/changes/active-options-runtime-self-heal-20260319/tasks.md`
- Runtime / Infra Changes:
  - L0 写入治理：`DEPTH` 仅更新价格簿字段，flow 字段仅 `QUOTE/TRADE` 可写。
  - `ws_*_seen` 改为有效值语义（仅正值置位），避免零值污染后锁死 fallback。
  - ActiveOptions 新增行质量语义（`REAL/FALLBACK_SYNTHETIC/PLACEHOLDER`）与 fallback 原因。
  - `/debug/persistence_status.active_options` 新增 `rows_real_non_synthetic/rows_synthetic_fallback/last_fallback_mode`。
  - 验活脚本升级：`chain_size>0` 时必须至少 1 行 `row_quality=REAL`。
- Commands Run:
  - `./scripts/test/run_pytest.ps1 l0_ingest/tests/test_chain_state_store.py -q`
  - `./scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py -q`
  - `./scripts/test/run_pytest.ps1 app/tests/test_health_route_diagnostics.py -q`
  - `./scripts/test/run_pytest.ps1 l3_assembly/tests/test_payload_events.py l3_assembly/tests/test_presenters.py l3_assembly/tests/test_reactor.py -q`
  - `./scripts/ops/verify_active_options_hotfix.ps1`
  - `python scripts/diag/check_active_options_no_data_cause.py --json`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`
  - `C:\Program Files\PowerShell\7\pwsh.exe -File scripts/validate_session.ps1 -Strict`

## Verification
- Passed:
  - `l0_ingest/tests/test_chain_state_store.py`: 9 passed
  - `shared/services/active_options/test_runtime_service.py`: 21 passed
  - `app/tests/test_health_route_diagnostics.py`: 1 passed
  - `l3_assembly tests (payload/presenters/reactor)`: 77 passed
  - `scripts/validate_session.ps1 -Strict` (pwsh): PASS
- Failed / Not Run:
  - `scripts/ops/verify_active_options_hotfix.ps1`: 本 shell `WinError 10106`（127.0.0.1 provider init failed）
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`: Windows PowerShell host error `8009001d`

## Pending
- Must Do Next:
  - 在用户终端（网络栈正常）执行在线验活，确认 `quality_real>=1` 的 PASS 输出。
- Nice to Have:
  - 前端 debug 视图补充 `row_quality/fallback_reason`，提升线上排障效率。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本次 P0 范围已闭环，未引入新增技术债
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-21
- DEBT-RISK: 本机网络栈异常会影响在线验活与现场排障速度
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: n/a
- RUNTIME-ARTIFACT-EXEMPT: 无 runtime artifact 变更

## How To Continue
- Start Command:
  - `./scripts/ops/start_backend.ps1 -Foreground`
- Key Logs:
  - `logs/backend_runtime.current.log`
- First File To Read:
  - `shared/services/active_options/runtime_service.py`

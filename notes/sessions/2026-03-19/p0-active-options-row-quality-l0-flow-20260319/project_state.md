# Project State

## Snapshot
- DateTime (ET): 2026-03-19 13:12:17 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `d64eb98`
- Environment:
  - Market: `OPEN`
  - Data Feed: `DEGRADED` (current shell `WinError 10106`)
  - L0-L4 Pipeline: `DEGRADED` (live HTTP verify blocked in this shell)

## Current Focus
- Primary Goal: 关闭 ActiveOptions P0（L0 flow 字段污染 + 合成行防伪 + 门禁升级）。
- Scope In:
  - L0: `DEPTH` 与 flow 字段写入隔离；`ws_*_seen` 正值语义。
  - ActiveOptions: `row_quality/fallback_reason/is_synthetic_fallback` 可选契约。
  - Diagnostics: `rows_real_non_synthetic/rows_synthetic_fallback/last_fallback_mode`。
  - Gate: `verify_active_options_hotfix.ps1` 升级为 `row_quality=REAL` 判据。
  - OpenSpec/SOP/Session 同步与 strict 留痕。
- Scope Out:
  - OS 网络栈修复（`WinError 10106`）。

## What Changed (Latest Session)
- Files:
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
- Behavior:
  - DEPTH 不再覆写 `volume/current_volume/turnover`，flow 字段污染路径被切断。
  - `ws_volume_seen/ws_current_volume_seen/ws_turnover_seen` 仅在正值时置位，避免 `0` 锁死 REST fallback。
  - ActiveOptions fallback 输出显式标记 `FALLBACK_SYNTHETIC`，主路径输出 `REAL`，占位输出 `PLACEHOLDER`。
  - `/debug/persistence_status.active_options` 可区分 `rows_real_non_synthetic` 与合成回退行。
  - 验活脚本在 `chain_size>0` 时要求至少一行 `row_quality=REAL`。
- Verification:
  - `./scripts/test/run_pytest.ps1 l0_ingest/tests/test_chain_state_store.py -q` -> 9 passed
  - `./scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py -q` -> 21 passed
  - `./scripts/test/run_pytest.ps1 app/tests/test_health_route_diagnostics.py -q` -> 1 passed
  - `./scripts/test/run_pytest.ps1 l3_assembly/tests/test_payload_events.py l3_assembly/tests/test_presenters.py l3_assembly/tests/test_reactor.py -q` -> 77 passed
  - `python scripts/diag/check_active_options_no_data_cause.py --json` -> 运行成功（本机 HTTP 端点不可达）
  - `./scripts/ops/verify_active_options_hotfix.ps1` -> 因 `WinError 10106` 失败
  - `C:\Program Files\PowerShell\7\pwsh.exe -File scripts/validate_session.ps1 -Strict` -> PASS

## Risks / Constraints
- Risk 1: 当前 shell 仍存在 `WinError 10106`，在线验活需在用户可用网络栈终端执行。
- Risk 2: 工作树含大量历史改动，本次未回滚任何非本任务文件。

## Next Action
- Immediate Next Step: 在用户终端重启后端并执行 `verify_active_options_hotfix.ps1`，确认 `quality_real>=1` 持续成立。
- Owner: Codex/User

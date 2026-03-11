# Handoff

## Session Summary
- DateTime (ET): 2026-03-11 09:21:01 -04:00
- Goal: 系统性审计并修复 Option_v3 全链路 GPU 重复计算与算力浪费（至少 P0/P1）。
- Outcome: 已完成 P0/P1 修复并补齐运行时证据链（tick/version/compute_id/gpu_task_id）与回归测试。

## What Changed
- Code / Docs Files:
  - app/loops/compute_loop.py
  - app/loops/housekeeping_loop.py
  - app/loops/shared_state.py
  - l0_ingest/feeds/option_chain_builder.py
  - l1_compute/reactor.py
  - l1_compute/tests/test_reactor.py
  - app/loops/tests/test_compute_loop_gpu_dedup.py
  - app/loops/tests/test_housekeeping_gpu_dedup.py
  - docs/SOP/L0_DATA_FEED.md
  - docs/SOP/L1_LOCAL_COMPUTATION.md
- Runtime / Infra Changes:
  - `fetch_chain` 增加兼容参数 `include_legacy_greeks`（默认 `false`），默认不再触发 legacy Greeks 重算。
  - `compute_loop` 基于 `snapshot_version` 去重，重复版本直接 skip，避免重复 GPU 提交。
  - `housekeeping_loop` 复用 `SharedLoopState.latest_l1_snapshot` 并按版本去重。
  - L1 增加 GPU 审计日志与 `computed_gamma/computed_vanna` 输出列。
- Commands Run:
  - powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId gpu-duplicate-compute-audit -Title "GPU duplicate compute and capacity waste audit" -Scope "audit + p0p1 fixes" -Owner "Codex" -ParentSession "2026-03-11/startup_doc_rewrite_live_boot" -Timezone "Eastern Standard Time"
  - powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 app/loops/tests/test_compute_loop_helpers.py app/loops/tests/test_compute_loop_gpu_dedup.py app/loops/tests/test_housekeeping_gpu_dedup.py l1_compute/tests/test_reactor.py
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict

## Verification
- Passed:
  - `app/loops/tests/test_compute_loop_helpers.py`
  - `app/loops/tests/test_compute_loop_gpu_dedup.py`
  - `app/loops/tests/test_housekeeping_gpu_dedup.py`
  - `l1_compute/tests/test_reactor.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`（Session validation passed）
- Failed / Not Run:
  - 无（目标回归集全部通过）

## Pending
- Must Do Next:
  - 无阻断项。
- Nice to Have:
  - 增加线上 Prometheus 面板展示 `gpu_compute_audit` 计数趋势。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本 session 内无未完成勾选项。
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-16
- DEBT-RISK: 低；遗留兼容路径仅在显式启用 `include_legacy_greeks=true` 时产生额外负载。
- DEBT-NEW: 0
- DEBT-CLOSED: 2
- DEBT-DELTA: -2
- DEBT-JUSTIFICATION: N/A
- RUNTIME-ARTIFACT-EXEMPT: N/A

## How To Continue
- Start Command:
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict
- Key Logs:
  - [GPU-AUDIT] duplicate snapshot skipped ...
  - [GPU-AUDIT] l1_dispatch tick_id=... snapshot_version=... compute_id=... gpu_task_id=...
- First File To Read:
  - app/loops/compute_loop.py

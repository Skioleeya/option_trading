# Handoff

## Session Summary
- DateTime (ET): 2026-03-19 11:16:59 -04:00
- Goal: 修复 `start_backend.ps1 -Foreground` NativeCommandError，以及 ActiveOptions 在 `chain_size>0` 场景长期全占位问题。
- Outcome: 两项修复已落地并通过目标测试；strict validation 已通过。

## What Changed
- Code / Docs Files:
  - `scripts/ops/start_backend.ps1`
  - `shared/services/active_options/runtime_service.py`
  - `shared/services/active_options/runtime_service_support.py`
  - `shared/services/active_options/test_runtime_service.py`
  - `notes/sessions/2026-03-19/fix-start-backend-active-options-fallback-20260319/project_state.md`
  - `notes/sessions/2026-03-19/fix-start-backend-active-options-fallback-20260319/open_tasks.md`
  - `notes/sessions/2026-03-19/fix-start-backend-active-options-fallback-20260319/handoff.md`
  - `notes/sessions/2026-03-19/fix-start-backend-active-options-fallback-20260319/meta.yaml`
- Runtime / Infra Changes:
  - Foreground 启动路径由 PowerShell 直接调用 python 改为 `cmd /c` 包裹执行，避免 uvicorn stderr 被提升为 `NativeCommandError`。
  - ActiveOptions 归一化兼容别名字段（含 `currentVolume/amount/openInterest/strike_price/last_done/iv/hv` 等）。
  - 当 `chain` 非空但无 `turnover/open_interest` 可用候选时，启用 hard fallback 并注入最小 `volume`，避免 5 行占位长期持续。
  - fallback 日志区分 `turnover/open_interest` fallback 与 `hard fallback`。
- Commands Run:
  - `./scripts/test/run_pytest.ps1 shared/services/active_options/test_runtime_service.py -q`
  - `./scripts/ops/start_backend.ps1 -Foreground -HotfixActiveOptions -HotfixMinVolume 10 -DryRun`
  - `./scripts/validate_session.ps1 -Strict`

## Verification
- Passed:
  - `shared/services/active_options/test_runtime_service.py`: 18 passed
  - `start_backend.ps1` hotfix foreground dry-run: pass
  - `validate_session.ps1 -Strict`: pass
- Failed / Not Run:
  - 在线实盘验活未在当前 shell 完成（需用户终端执行并确认 `/history` 实时行）。

## Pending
- Must Do Next:
  - 在用户终端执行：
    - `./scripts/ops/start_backend.ps1 -Foreground -HotfixActiveOptions -HotfixMinVolume 10`
    - `./scripts/ops/verify_active_options_hotfix.ps1`
  - 验证 `chain_size>0` 时 `active_options real>=1`。
- Nice to Have:
  - 将硬回退策略扩展为时段化阈值与质量评分（区分“连续性兜底”与“高置信候选”）。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 在线验活依赖主机网络连通性与网关可达性，本轮仅完成代码侧修复与离线验证。
- DEBT-OWNER: User/Codex
- DEBT-DUE: 2026-03-21
- DEBT-RISK: 若网关仍不可达，活跃榜单可能持续由降级路径驱动，信号质量受限。
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: n/a
- RUNTIME-ARTIFACT-EXEMPT: n/a
- SOP-EXEMPT: 本次仅涉及 `shared/services` 与运维脚本行为修复，未修改 L0/L1/L2/L3/L4/app 运行时合同。
- OPENSPEC-EXEMPT: hotfix scoped to startup script wrapping and shared ActiveOptions fallback robustness; no new contract/proposal chain created in this session.

## How To Continue
- Start Command:
  - `./scripts/ops/start_backend.ps1 -Foreground -HotfixActiveOptions -HotfixMinVolume 10`
- Key Logs:
  - `logs/backend_runtime.current.log`
- First File To Read:
  - `shared/services/active_options/runtime_service_support.py`

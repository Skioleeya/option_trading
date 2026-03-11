# Handoff

## Session Summary
- DateTime (ET): 2026-03-11 15:48:56 -04:00
- Goal: 继续逐 tick 检查 Depth Profile 是否在更新并同步到页面。
- Outcome: 在线逐 tick 对账完成；30/30 匹配且 29 个变化 tick 在 UI 同步体现，确认 Depth Profile 在持续更新。

## What Changed
- Code / Docs Files:
  - scripts/diagnostics/reconcile_depth_profile_online.py
  - notes/context/project_state.md
  - notes/context/open_tasks.md
  - notes/context/handoff.md
  - notes/sessions/2026-03-11/tradingview-depth-profile-online-reconcile/project_state.md
  - notes/sessions/2026-03-11/tradingview-depth-profile-online-reconcile/open_tasks.md
  - notes/sessions/2026-03-11/tradingview-depth-profile-online-reconcile/handoff.md
  - notes/sessions/2026-03-11/tradingview-depth-profile-online-reconcile/meta.yaml
- Runtime / Infra Changes:
  - 无运行时代码改动；新增验证脚本与证据输出。
- Commands Run:
  - powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId tradingview-depth-profile-online-reconcile -Title "TradingView depth profile online reconcile" -Scope "verification" -Owner "Codex" -ParentSession "2026-03-11/tradingview-net-gex-online-reconcile" -Timezone "Eastern Standard Time"
  - python scripts/diagnostics/reconcile_depth_profile_online.py --samples 30 --out-dir tmp/reconcile
  - python scripts/diagnostics/reconcile_depth_profile_online.py --samples 5 --out-dir tmp/reconcile
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict

## Verification
- Passed:
  - 30 tick 对账：captured=30, match=30, mismatch=0
  - 变化一致性：expected_changed=29, observed_changed=29
  - 5 tick smoke：captured=5, match=5, mismatch=0
- Failed / Not Run:
  - 无

## Pending
- Must Do Next:
  - 如需更长窗口，可执行 200 tick 连续监测并生成单独证据集。
- Nice to Have:
  - 增加行级差异导出（具体哪一行 strike/宽度变化）。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本次仅新增验证脚本，无新增运行时技术债。
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-13
- DEBT-RISK: 低；未触及运行时代码。
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: N/A
- RUNTIME-ARTIFACT-EXEMPT:
  - N/A

## How To Continue
- Start Command:
  - python scripts/diagnostics/reconcile_depth_profile_online.py --samples 100 --out-dir tmp/reconcile
- Key Logs:
  - tmp/reconcile/depth_profile_reconcile_20260311T194657Z.json
  - tmp/reconcile/depth_profile_reconcile_20260311T194821Z.json
- First File To Read:
  - scripts/diagnostics/reconcile_depth_profile_online.py

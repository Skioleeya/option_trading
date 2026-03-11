# Handoff

## Session Summary
- DateTime (ET): 2026-03-11 15:38:01 -04:00
- Goal: 构建在线 1:1 对账脚本，严格比对 WS 原始 `net_gex` 与页面显示值。
- Outcome: 脚本完成并完成两次实盘采样，结果均 100% 匹配。

## What Changed
- Code / Docs Files:
  - scripts/diagnostics/reconcile_net_gex_online.py
  - notes/context/project_state.md
  - notes/context/open_tasks.md
  - notes/context/handoff.md
  - notes/sessions/2026-03-11/tradingview-net-gex-online-reconcile/project_state.md
  - notes/sessions/2026-03-11/tradingview-net-gex-online-reconcile/open_tasks.md
  - notes/sessions/2026-03-11/tradingview-net-gex-online-reconcile/handoff.md
  - notes/sessions/2026-03-11/tradingview-net-gex-online-reconcile/meta.yaml
- Runtime / Infra Changes:
  - 无运行时代码变更；新增验证脚本与证据输出。
- Commands Run:
  - powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId tradingview-net-gex-online-reconcile -Title "TradingView net gex online reconcile" -Scope "verification" -Owner "Codex" -ParentSession "2026-03-11/tradingview-hard-cut-archive-proposals" -Timezone "Eastern Standard Time"
  - python scripts/diagnostics/reconcile_net_gex_online.py --samples 30 --out-dir tmp/reconcile
  - python scripts/diagnostics/reconcile_net_gex_online.py --samples 5 --out-dir tmp/reconcile
  - powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict

## Verification
- Passed:
  - 在线对账（30 tick）: captured=30, match=30, mismatch=0
  - smoke（5 tick）: captured=5, match=5, mismatch=0
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`: Session validation passed.
- Failed / Not Run:
  - 无

## Pending
- Must Do Next:
  - 如需更高置信度，可扩大采样窗口（100/200 tick）。
- Nice to Have:
  - 增加可选字段：页面颜色 class 与方向语义断言（红/绿）。

## Debt Record (Mandatory)
- DEBT-EXEMPT: 本次仅新增验证脚本，无未闭环运行时技术债。
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-13
- DEBT-RISK: 低；不涉及生产路径逻辑变更。
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: N/A
- RUNTIME-ARTIFACT-EXEMPT:
  - N/A

## How To Continue
- Start Command:
  - python scripts/diagnostics/reconcile_net_gex_online.py --samples 50 --out-dir tmp/reconcile
- Key Logs:
  - tmp/reconcile/net_gex_reconcile_20260311T193559Z.json
  - tmp/reconcile/net_gex_reconcile_20260311T193728Z.json
- First File To Read:
  - scripts/diagnostics/reconcile_net_gex_online.py

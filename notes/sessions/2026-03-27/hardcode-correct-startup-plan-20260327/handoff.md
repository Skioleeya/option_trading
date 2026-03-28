# Handoff

## Session Summary
- DateTime (ET): 2026-03-27 09:40:42 -04:00
- Goal: write the correct startup procedure permanently into `AGENTS.md` with only 1-3 lines.
- Outcome: added a 2-line hard rule to `AGENTS.md` that makes real-host startup mandatory for live broker-dependent checks and fixes startup order to strict first, degraded only after real-host broker connectivity failure.

## What Changed
- Code / Docs Files:
  - `AGENTS.md`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-03-27/hardcode-correct-startup-plan-20260327/project_state.md`
  - `notes/sessions/2026-03-27/hardcode-correct-startup-plan-20260327/open_tasks.md`
  - `notes/sessions/2026-03-27/hardcode-correct-startup-plan-20260327/handoff.md`
  - `notes/sessions/2026-03-27/hardcode-correct-startup-plan-20260327/meta.yaml`
- Runtime / Infra Changes:
  - none
- Commands Run:
  - `powershell -ExecutionPolicy Bypass -File scripts/new_session.ps1 -TaskId hardcode-correct-startup-plan-20260327 -Title "Hardcode correct startup plan into AGENTS" -Scope "ops" -Owner "Codex" -ParentSession "2026-03-27/restart-backend-dataflow-repair-20260327" -Timezone "America/New_York" -UpdatePointer`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Verification
- Passed:
  - `AGENTS.md` contains exactly 2 new startup-rule lines under `## 11. Scripted Enforcement Summary`
  - the new rule explicitly forbids sandbox-local backend launches as evidence for live broker/runtime health
  - the new rule explicitly fixes startup order to strict first and `-Degraded` only after real-host broker connectivity failure
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed
- Failed / Not Run:
  - none

SOP-EXEMPT: governance-only documentation hardening; no runtime-layer behavior changed.
OPENSPEC-EXEMPT: governance-only documentation hardening; no runtime-layer behavior changed.

## Pending
- Must Do Next:
  - follow the new AGENTS startup rule on all future live restarts
- Nice to Have:
  - none

## Debt Record (Mandatory)
- DEBT-EXEMPT: session complete with no unresolved delivery debt
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-03-27
- DEBT-RISK: none
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION: not required; no net new debt was introduced
- RUNTIME-ARTIFACT-EXEMPT: validation diagnostics are runtime artifacts, not source deliverables

## How To Continue
- Start Command:
  - `powershell -ExecutionPolicy Bypass -File scripts/ops/start_backend.ps1 -LogFile logs/backend_runtime.current.log`
- Key Logs:
  - `logs/backend_runtime.current.log`
- First File To Read:
  - `AGENTS.md`

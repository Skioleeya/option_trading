# Project State

## Snapshot
- DateTime (ET): 2026-03-27 09:40:42 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6dfd9c5`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: hardcode the correct system startup procedure into `AGENTS.md` using only 1-3 instruction lines so future agents cannot repeat the sandbox-local restart mistake.
- Scope In:
  - `AGENTS.md`
  - `notes/context/*`
  - `notes/sessions/2026-03-27/hardcode-correct-startup-plan-20260327/*`
- Scope Out:
  - no runtime code changes
  - no SOP or OpenSpec content changes
  - no frontend/backend behavior changes

## What Changed (Latest Session)
- Files:
  - `AGENTS.md`
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-03-27/hardcode-correct-startup-plan-20260327/project_state.md`
  - `notes/sessions/2026-03-27/hardcode-correct-startup-plan-20260327/open_tasks.md`
  - `notes/sessions/2026-03-27/hardcode-correct-startup-plan-20260327/handoff.md`
  - `notes/sessions/2026-03-27/hardcode-correct-startup-plan-20260327/meta.yaml`
- Behavior:
  - added 2 hard-rule lines to `AGENTS.md` under the scripted enforcement section
  - the new rule requires live broker-dependent backend startup to run on the real host environment outside sandbox
  - the new rule fixes the startup order to strict first, `-Degraded` only after a real-host broker connectivity failure
- Verification:
  - `AGENTS.md` now contains the 2-line startup rule block
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Risks / Constraints
- Risk 1: this is governance hardening only; it prevents future operator error but does not itself change runtime code.
- Risk 2: future agents still need to follow the rule correctly when executing live restarts.

## Next Action
- Immediate Next Step: sync handoff/context and rerun strict validation so the new AGENTS rule is recorded under a green session.
- Owner: Codex

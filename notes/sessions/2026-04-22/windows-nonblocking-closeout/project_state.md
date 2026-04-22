# Project State

## Snapshot
- DateTime (ET): 2026-04-22 17:18
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `5583a978fbc33d0ae1b8550e493115f1ea6755ad`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Close the two remaining Windows non-blocking follow-ups from `windows-env-rollout`.
- Scope In: Restore local Git provenance in `Option_v4`; remove sandbox-local frontend `spawn EPERM` by hard-cutting the strict dev launcher to the Vite JS API path; sync SOP and session evidence.
- Scope Out: No broker/runtime contract changes, no new host migration wave, no Git history cleanup beyond restoring usable local provenance.

## What Changed (Latest Session)
- Files: `.git/` was restored into `Option_v4`; `l4_ui/vite.config.ts` was replaced by `l4_ui/vite.config.mjs`; `l4_ui/scripts/dev-strict.mjs` now starts Vite via the JS API; `docs/SOP/L4_FRONTEND.md` records the no-CLI rule for Windows constrained contexts.
- Behavior: `Option_v4` now resolves branch/head/origin locally instead of `unknown`; sandbox-local strict frontend startup no longer depends on the Vite CLI/esbuild child-process path that produced `spawn EPERM`.
- Verification: local `git rev-parse/branch/origin` all resolve; sandbox-local `node .\scripts\dev-strict.mjs --host 127.0.0.1 --port 5179 --strictPort` listens successfully; `npm --prefix l4_ui run build` stays green; host `manage.py start-all --verify-only` remains all-true.

## Risks / Constraints
- Risk 1: The restored `.git` metadata was copied from the sibling `Option_v3` worktree, so provenance is no longer `unknown` but history hygiene still reflects a copy-derived mirror rather than a fresh clone.
- Risk 2: Final runtime evidence still belongs to the real Windows host path; sandbox-local success only closes the frontend dev-launcher restriction, not the broker-dependent health authority.

## Next Action
- Immediate Next Step: Run `.\.venv\Scripts\python.exe manage.py validate-session --strict` and close the session.
- Owner: Codex

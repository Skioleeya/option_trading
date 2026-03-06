# Project State

## Snapshot
- DateTime (ET): 2026-03-06 12:13:49 -05:00
- Branch: `master`
- Last Commit: `00789bd`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Enforce isolated pytest cache + non-mixed execution context after cache-permission incident.
- Scope In:
  - Root pytest configuration (`pytest.ini`) for dedicated cache dir
  - Standardized pytest wrapper script with non-admin guard
  - Docs and ignore rules to prevent cache artifacts entering workspace noise
- Scope Out:
  - Unrelated strategy logic changes in AgentA/AgentB/AgentG
  - Destructive cleanup (`reset --hard`, unreviewed deletes)

## What Changed (Latest Session)
- Files:
  - `AGENTS.md`
  - `pytest.ini`
  - `.gitignore`
  - `scripts/test/run_pytest.ps1`
  - `scripts/README.md`
- Behavior:
  - Added AGENTS hard mandate (Section 4.1) for pytest single-entry, non-admin context, and cache isolation.
  - Pytest cache directory is fixed to `tmp/pytest_cache`.
  - Standard wrapper now blocks Administrator context to avoid mixed-permission cache artifacts.
  - Team docs updated to run tests via wrapper entry.
- Verification:
  - Removed stale `.pytest_cache` and re-ran wrapper test.
  - Confirmed `NO_.pytest_cache` and `HAS_tmp/pytest_cache` after execution.

## Risks / Constraints
- Risk 1: Existing `pytest-cache-files-*` directories remain permission-locked until manual deletion by owner/admin.
- Risk 2: Direct `pytest` invocation (bypassing wrapper) can still be run by humans and reintroduce mixed context.

## Next Action
- Immediate Next Step: Team adopts `scripts/test/run_pytest.ps1` as default test command.
- Owner: Codex

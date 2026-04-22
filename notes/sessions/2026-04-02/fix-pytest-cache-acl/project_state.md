# Project State

## Snapshot
- DateTime (ET): 2026-04-02 08:32:10 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `7fb0f53`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: restore host-side write access to `tmp/pytest_cache` and make pytest fail fast with a deterministic ACL error instead of a late cache warning
- Scope In:
  - `scripts/test/run_pytest.ps1`
  - `scripts/test/repair_pytest_cache_acl.ps1`
  - `scripts/README.md`
  - session/context records for this ACL remediation
- Scope Out:
  - runtime source files
  - OpenSpec records
  - SOP documents

## What Changed (Latest Session)
- Files:
  - updated `scripts/test/run_pytest.ps1`
  - added `scripts/test/repair_pytest_cache_acl.ps1`
  - updated `scripts/README.md`
- Behavior:
  - the pytest wrapper now probes `tmp/pytest_cache` writeability before launching pytest and throws a targeted remediation message when the cache path is not writable
  - added a dedicated repair script to normalize `tmp/pytest_cache` ownership/ACLs in the real host context
  - host-level verification confirmed writes at the cache root and under `tmp/pytest_cache/research_store_tests` after the repair pass
- Verification:
  - host-level `Set-Content` probe to `tmp/pytest_cache` passed
  - host-level `New-Item` probe under `tmp/pytest_cache/research_store_tests` passed
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 tests/active_options -q` passed (`32 passed`)

## Risks / Constraints
- Risk 1: the constrained Codex shell still cannot write directly under `tmp/pytest_cache`, so verification had to use unrestricted host-context commands to reflect the real local runtime behavior
- Risk 2: if another tool or account re-owns `tmp/pytest_cache` later, the repair script must be rerun before the non-admin pytest wrapper will work again on the host

## Next Action
- Immediate Next Step: reuse `scripts/test/run_pytest.ps1` normally; if cache writes regress on the host, rerun `scripts/test/repair_pytest_cache_acl.ps1` and recheck `tmp/pytest_cache/research_store_tests`
- Owner: Codex

# Open Tasks

## Priority Queue
- [x] P0: Strict gate hardening for anti-garbage code quality
  - Owner: Codex
  - Definition of Done:
    - `validate_session.ps1 -Strict` invokes quality gate + openspec chain gate
    - strict fails on gate failures
  - Blocking: None
- [x] P0: CI session-validation workflow path correction
  - Owner: Codex
  - Definition of Done:
    - workflow calls `scripts/policy/check_layer_boundaries.ps1`
  - Blocking: None
- [x] P1: Boundary policy tightening
  - Owner: Codex
  - Definition of Done:
    - layer boundary rules include wildcard import ban and stronger layer constraints
  - Blocking: None
- [ ] P1: Enforce GitHub branch protection required check (`validate-session`)
  - Owner: Repo Admin
  - Definition of Done:
    - `validate-session` configured as required status check for protected branch
  - Blocking: GitHub admin permission

## Parking Lot
- [ ] Calibrate `scripts/policy/quality_thresholds.json` hot-path patterns and duplicate window size after 3 PRs evidence.
- [ ] Consider adding circular dependency static gate for Python import graph.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] anti-garbage-code-gate-hardening governance pack implemented (2026-03-13 00:53 ET)

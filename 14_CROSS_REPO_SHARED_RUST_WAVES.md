# Cross-Repo Shared Rust Migration Plan

## Objective

Complete the remaining `shared/*` Rust cutover through cross-repo migration waves instead of `shared`-local cleanup.

This plan is mandatory because the remaining `shared/contracts/*`, `shared/models/*`, `shared/system/*`, and `shared/services/*` Python owners are still consumed directly by downstream Python code outside `shared/`.

## Blocking Reality

Measured live imports from outside `shared/` into `shared.contracts.*`, `shared.models.*`, `shared.system.*`, or `shared.services.*`: `80`

Therefore:
- `shared` cannot be completed in isolation
- each remaining owner group requires synchronized consumer rewrites
- implementation waves must be cross-repo, not directory-local

## Execution Order

1. Wave 1: `shared/contracts/*` + all live consumers
2. Wave 2: `shared/models/*` + all live consumers
3. Wave 3: `shared/system/*` and `shared/services/*` + all live consumers

## Hard Rules

- planning and runtime code changes must not happen in the same slice
- no wave may claim completion unless all mapped consumers are migrated or retired in the same execution program
- no new Python compatibility bridge may be introduced unless explicitly governed
- constants/config ownership remains single-source
- Rust owners must replace Python owners, not duplicate them
- each wave must update SOPs if runtime behavior or contract behavior changes
- each wave must pass OpenSpec chain gate and `scripts/validate_session.ps1 -Strict`

## Wave Gate Model

Every wave must satisfy all gates:
- owner group inventory frozen
- live consumer set frozen
- cutover order defined
- rollback radius bounded
- tests mapped
- SOP impact mapped
- OpenSpec execution evidence recorded
- strict validation green

## Exit Criteria

The shared Rust cutover is only complete when:
- the targeted `shared/*` Python owner files are retired
- all downstream Python consumers are rewritten to Rust-owned or Rust-backed interfaces
- no deleted `shared/*` owner path remains in live imports
- no compatibility-only Python owner remains on the main runtime path

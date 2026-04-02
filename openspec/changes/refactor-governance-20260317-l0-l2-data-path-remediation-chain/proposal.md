## Why

The L0-L2 remediation child proposals already exist and reference a governance parent,
but the parent record is missing from `openspec/changes`. This breaks the OpenSpec
parent/child chain gate and leaves the dependency lineage non-auditable.

## What Changes

Create the missing parent governance change record:
- `refactor-governance-20260317-l0-l2-data-path-remediation-chain`

This parent governs existing child proposals:
1. `refactor-dependency-20260324-l0-v2-single-direction-tree`
2. `refactor-dependency-20260324-l0-runtime-contract-single-source`
3. `refactor-dependency-20260324-atm-decay-after-hours-replay-path`
4. `refactor-dependency-20260325-atm-decay-capture-stall-diagnostics`

## Scope

- OpenSpec governance metadata restoration only
- parent-child chain integrity repair
- no runtime behavior changes

## Rollback

If chain governance reconstruction is incorrect, revert this parent folder and recreate
with corrected child mapping.

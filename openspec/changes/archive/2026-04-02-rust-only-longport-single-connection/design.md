## Context

`Option_v3` currently carries dual ownership for quote access. The runtime must converge to one long-lived quote path while preserving L0-L4 contract continuity (`rust_active`, `shm_stats`, and source timestamps).

## Goals

- Eliminate dual long-lived quote contexts for a single account.
- Preserve L0-L4 payload continuity in degraded mode.
- Enforce deterministic migration sequencing.

## Non-Goals

- Rewriting L1/L2/L3 business engines.
- Changing L0->L4 timestamp semantics.

## Parent Controls

1. **Dependency Lock**: child A must merge before B; B before C.
2. **Contract Lock**: `rust_active`, `shm_stats`, `data_timestamp/timestamp` semantics remain unchanged.
3. **Completion Lock**: parent closes only after all children pass strict validation.

## Risk Controls

- If runtime degraded mode emits stale snapshots instead of explicit empty-chain diagnostics, block completion.
- If child introduces forbidden cross-layer imports, block completion.
- If strict session gate fails, parent remains open.


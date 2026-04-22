## Context

`shared` is the current Python concentration point, and `L0` already contains a Rust seed that is not yet the runtime owner. This child proposal must convert the module-audit document into a governed, implementation-facing boundary definition that can be executed later without architecture drift.

## Goals

- define a bounded first-wave Rust migration slice for `shared + L0`
- classify modules by role, migration class, and risk
- force decomposition before any mixed-responsibility runtime path is treated as migration-ready
- preserve high cohesion and low coupling at crate and module boundaries

## Non-Goals

- no actual runtime migration implementation
- no L1, L2, L3, or app migration planning beyond explicit exclusion
- no redefinition of contract or constants governance already defined upstream

## Controls

1. Contract, compute, runtime, and compat-shim roles must be separated explicitly.
2. No mixed-responsibility file may be treated as migration-ready before decomposition.
3. `shared/system` may only enter the early set for IPC and diagnostics-bearing submodules.
4. `shared/services/l0_runtime/*` must decompose into bootstrap, subscription, state, snapshot, degraded-mode, and diagnostics responsibilities.
5. `shared/services/active_options/*` must preserve deterministic kernel boundaries and row-quality semantics.
6. Boundary claims must reference a concrete first-wave artifact rather than abstract migration intent.

## Risk Controls

- If `shared` remains a generic catch-all bucket, block closure.
- If `l0_rust` remains framed only as an accelerator rather than a runtime owner target, block closure.
- If first-wave scope expands into L1/L2/L3/app, block closure.
- If rollback radius is undefined, block closure.
- If entry conditions for implementation sessions are not explicit, block closure.

## Execution Model

This child advances through three states:

1. `created`
   - proposal, design, tasks, and spec exist
   - dependency order is fixed behind dependency and magic-number
2. `validated`
   - boundary evidence package exists
   - first-wave set, exclusion set, validation matrix, and rollback radius are explicit
   - upstream contract and constants/config rules are consumed without contradiction
3. `closable`
   - implementation-session entry gate is accepted as sufficient
   - no mixed-responsibility module is falsely marked migration-ready
   - strict validation evidence is present in session handoff

The target for this session is `validated`, not `closable`.

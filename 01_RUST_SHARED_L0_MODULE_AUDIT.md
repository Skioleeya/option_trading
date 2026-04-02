# Rust Migration Detailed Document 01 - Shared and L0 Module Audit

## 1. Objective
This document defines the first executable migration boundary for converting the backend runtime toward pure Rust. The scope is limited to `shared` and `l0_ingest`, because these areas have the highest leverage on contract ownership, runtime determinism, and dependency reduction.

## 2. Scope and Boundary
Included:
- `shared/contracts/*`
- `shared/models/*`
- `shared/system/*`
- `shared/services/l0_runtime/*`
- `shared/services/active_options/*`
- `l0_ingest/l0_rust/*`

Excluded for this phase:
- `l1_compute/*`
- `l2_decision/*`
- `l3_assembly/*`
- `app/*`
- `l4_ui/*`

Rationale:
- `shared` is the current cross-layer Python concentration point.
- `L0` owns source-time semantics and runtime ingress.
- Moving higher layers before these two would increase coupling and make regression attribution unreliable.

## 3. Current State Summary
Observed codebase distribution:
- `shared`: Python-heavy, no native Rust ownership at the contract/runtime-service layer.
- `l0_ingest`: already has an existing Rust seed (`l0_rust`), but current shape is still extension-oriented rather than runtime-native.
- `shared/services/l0_runtime/*`: primary Python runtime choke point.
- `shared/services/active_options/*`: already modular enough to become an early Rust runtime target.

Observed architectural reality:
- Existing Rust is present, but much of it is still used as an acceleration path rather than the primary runtime owner.
- Contract ownership is not yet centralized in Rust.
- Runtime constants and threshold semantics still need authoritative governance.

## 4. Migration Classification Model
Every module in `shared` and `L0` must be assigned one primary role.

Role classes:
- `Contract`: schema, DTO, enums, event payloads.
- `Compute`: deterministic pure logic with no transport or IO.
- `Runtime`: IO, orchestration, subscriptions, health, retries, transport, stateful runtime services.
- `CompatShim`: temporary Python bridge retained only to support transitional cutover.

Migration decision classes:
- `RustFirst`: migrate in the first wave.
- `RustSoon`: migrate after first-wave dependencies settle.
- `Defer`: keep for a later phase because the interface or ownership is still unstable.

Risk levels:
- `Low`: stable contract, low hidden state, low external binding risk.
- `Medium`: stable purpose, but some runtime coordination or config coupling exists.
- `High`: external SDK binding, ambiguous ownership, or mixed responsibility.

## 5. Shared Module Audit

### 5.1 shared/contracts
Primary role: `Contract`
Migration class: `RustFirst`
Risk: `Low`

Why:
- This directory should become the Rust source of truth for all cross-layer structures.
- It is the cleanest place to start contract centralization.

Required outcome:
- Rust-owned canonical event and payload definitions.
- Python uses generated or mirrored compatibility adapters only during transition.

Exit criteria:
- No contract-defining field list remains Python-authoritative.

### 5.2 shared/models
Primary role: `Contract`
Migration class: `RustFirst`
Risk: `Low`

Why:
- Most model structures are stable and can be owned by Rust without changing runtime behavior.
- This is a dependency reducer for later `L1`, `L2`, and `L3` migration.

Required outcome:
- Rust model ownership for cross-layer stable structures.
- Explicit separation between domain models and transport wrappers.

Exit criteria:
- Runtime paths consume Rust-defined models, not duplicated Python dataclass variants.

### 5.3 shared/system
Primary role: `Runtime`
Migration class: `RustSoon`
Risk: `Medium`

Why:
- This area often contains process-level concerns, IPC support, shared state utilities, and diagnostics hooks.
- It should move after contract and constants governance are stable.

Required outcome:
- Rust-owned IPC helpers and diagnostics carriers.
- No Python-only transport helper remains on the main runtime path.

Exit criteria:
- Transport state, IPC contracts, and diagnostics transport are Rust-native.

### 5.4 shared/services/l0_runtime
Primary role: `Runtime`
Migration class: `RustFirst`
Risk: `High`

Why:
- This is the actual ingress runtime center.
- It is where subscription logic, rate limiting, startup fallback, and source health semantics tend to concentrate.

Known migration blockers:
- External SDK integration boundaries.
- Existing Python orchestration around quote runtime bootstrap.
- Hidden retry/backoff and degraded-mode semantics.

Required decomposition before migration:
- bootstrap
- subscription management
- runtime state store
- snapshot projection
- degraded-mode policy
- diagnostics projection

Exit criteria:
- Python is no longer the owner of quote ingestion lifecycle or snapshot state.

### 5.5 shared/services/active_options
Primary role: `Compute` plus light `Runtime`
Migration class: `RustFirst`
Risk: `Medium`

Why:
- This module family is already cohesive.
- The core ranking, fallback selection, and quality annotations are deterministic enough to port early.
- It touches live payload quality and offers a contained validation surface.

Required decomposition before migration:
- candidate filtering
- ranking logic
- fallback policy
- row quality annotation
- runtime service wrapper

Exit criteria:
- Core active-options selection kernel runs in Rust.
- Python wrapper, if retained temporarily, is a narrow compatibility layer only.

## 6. L0 Audit

### 6.1 l0_ingest/l0_rust
Primary role: `Runtime`
Migration class: `RustFirst`
Risk: `Medium`

Current state:
- Rust already exists in `l0_rust`.
- The current design indicates an extension-bridged path rather than a fully Rust-native service owner.

Required target state:
- Rust owns subscription lifecycle.
- Rust owns in-memory normalized market state.
- Rust owns snapshot projection and Arrow handoff.
- Rust exports diagnostics and degraded markers directly.

Gap to close:
- move from "Rust as accelerator" to "Rust as runtime owner"

Exit criteria:
- `L0` can run without Python as the main source-of-truth process.

## 7. First-Wave Migration Set
The first-wave candidate set should be limited to modules that satisfy all of the following:
- stable contract surface
- deterministic compute or runtime behavior
- no UI semantics
- measurable dependency reduction
- bounded rollback radius

First-wave set:
- `shared/contracts/*`
- `shared/models/*`
- `shared/services/active_options/*` core kernel
- `shared/services/l0_runtime/*` decomposed runtime submodules
- `l0_ingest/l0_rust/*` promotion from bridge role to runtime-owner role

Do not include in wave 1:
- `L1` trackers
- `L2` strategy logic
- `L3` presenter-facing formatting
- `app` service routing

## 8. Recommended Work Breakdown

### Wave A: Ownership and decomposition
- classify every `shared + L0` module by role and risk
- split mixed-responsibility files before porting
- freeze constants ownership and contract boundaries

### Wave B: Rust contract and constants base
- create Rust source-of-truth crates for contracts and constants
- add compatibility mapping for Python readers

### Wave C: Runtime and compute kernel migration
- port `active_options` kernel
- port `l0_runtime` decomposed submodules
- promote `l0_rust` to runtime-owner

### Wave D: Controlled cutover
- dual-run compare
- diagnostics comparison
- explicit rollback switch
- retire Python runtime ownership

## 9. Verification Matrix
For each migrated module, verify the following:
- contract parity
- source-time parity
- diagnostics continuity
- degraded-mode continuity
- startup safety
- rollback path
- no hidden constant duplication

Additional L0-specific checks:
- snapshot monotonicity
- source timestamp stability
- SHM or Arrow handoff integrity
- no silent runtime fallback

Additional active-options checks:
- ranking parity
- sparse fallback parity
- real-versus-synthetic row quality semantics

## 10. Implementation Risks
- Hidden runtime state coupled into Python bootstrap helpers.
- External SDK constraints around Rust ownership.
- Constants duplication during transition.
- Contract drift if Python mirrors continue evolving after Rust ownership begins.

## 11. Governance Rules for This Phase
- No hardcoded thresholds in ported Rust modules.
- No mixed contract and runtime logic in one file.
- No new Python-only helper introduced into `shared` for runtime ownership.
- No promotion of `L1`, `L2`, or `L3` migration work before `shared + L0` exit criteria are met.

## 12. Review and Revision
Initial draft issue found during self-review:
- The earlier high-level plan treated `shared/system` as a single migration bucket, which was too broad for execution.

Revision applied:
- `shared/system` is now explicitly positioned as `RustSoon`, not blindly `RustFirst`.
- Only IPC and diagnostics-bearing submodules should enter the early migration set.

Normative review conclusion:
- The scope is cohesive.
- The dependency cut is scientifically correct.
- The wave breakdown is executable.
- The rollback radius is bounded.

Landing feasibility conclusion:
- This document is actionable as the first phase execution boundary.

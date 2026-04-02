# Rust Migration Detailed Document 03 - Contract Freeze Checklist

## 1. Objective
This document defines the contract freeze required before substantive Rust migration work proceeds. The purpose is to eliminate schema drift, preserve timing semantics, and make every later implementation change auditable against a stable boundary.

## 2. Why Contract Freeze Comes First
If implementation migration starts before contract freeze, the system will change in two dimensions at once:
- code path ownership changes
- schema and semantic meaning drift

That makes regression attribution weak and rollback unsafe.

Therefore, contract freeze is a hard prerequisite.

## 3. Freeze Scope
The following contract surfaces must be frozen before shared and L0 migration proceeds.

### 3.1 L0 Input and Output
Freeze:
- source timestamp semantics
- normalized quote/depth/trade event schema
- snapshot shape
- Arrow handoff schema
- `rust_active`
- `shm_stats`
- diagnostics continuity metadata

Must remain invariant:
- `timestamp` and `data_timestamp` refer to source time, not broadcast time
- degraded-mode markers remain explicit
- startup safety diagnostics remain visible

### 3.2 L1 Input Surface
Freeze:
- `EnrichedSnapshot`
- dependency fields consumed by microstructure and active-options paths
- `extra_metadata.source_data_timestamp_utc`
- IV and anchor-related metadata required by downstream layers

Must remain invariant:
- source-time linkage
- real-versus-derived field meaning
- no hidden fallback reinterpretation

### 3.3 L2 Input and Output Surface
Freeze:
- feature inputs consumed by decision logic
- output signal/event contracts handed to L3
- state labels needed for guards and anti-oscillation policy

Must remain invariant:
- decision priority semantics
- guard ordering semantics
- event naming

### 3.4 L3 Output Surface
Freeze:
- payload schema consumed by `l4_ui`
- delta and full-refresh envelopes
- `ui_state.active_options`
- header volatility payload fields
- broadcast timestamp and heartbeat timestamp separation

Must remain invariant:
- payload field names
- broadcast versus source-time meaning
- diagnostics and degraded-state visibility

## 4. Freeze Artifacts
The freeze is not complete until all of these exist.

Required artifacts:
- canonical field inventory
- field type inventory
- semantic notes for every timestamp field
- ownership map for every contract file
- Rust source-of-truth definition plan
- compatibility mapping for Python transition readers

Recommended artifact form:
- contract matrix table
- per-contract invariant list
- per-contract drift tests

## 5. Required Freeze Checklist

### 5.1 Structural Checklist
- [ ] every cross-layer contract is enumerated
- [ ] every payload field has a single owner
- [ ] every timestamp field has semantic notes
- [ ] every enum-like string is centralized
- [ ] every optional field has explicit meaning
- [ ] every degraded-mode field is documented

### 5.2 Ownership Checklist
- [ ] Rust source-of-truth owner is identified
- [ ] Python mirror or adapter path is identified
- [ ] deprecated duplicate definitions are identified
- [ ] contract change authority is defined

### 5.3 Validation Checklist
- [ ] serialization parity is defined
- [ ] backward compatibility expectation is defined
- [ ] drift detection mechanism is defined
- [ ] cutover acceptance test is defined

## 6. Contract Categories and Suggested Owners

### 6.1 Event Contracts
Suggested Rust owner:
- `crates/contracts/src/events/*`

Includes:
- normalized ingest events
- decision events exposed to L3
- runtime status events if externally consumed

### 6.2 Snapshot Contracts
Suggested Rust owner:
- `crates/contracts/src/snapshots/*`

Includes:
- L0 snapshot
- enriched snapshot
- active-options row structures if cross-layer visible

### 6.3 Payload Contracts
Suggested Rust owner:
- `crates/contracts/src/payloads/*`

Includes:
- full payload
- delta payload
- UI state contracts
- diagnostics blocks delivered to front-end consumers

### 6.4 Diagnostics Contracts
Suggested Rust owner:
- `crates/contracts/src/diagnostics/*`

Includes:
- health state payloads
- degradation reasons
- persistence or capture debug contract surfaces if treated as stable API

## 7. Engineering Cohesion and Coupling Rules
Contract freeze only works if contract ownership is structurally separated from runtime implementation.

Mandatory structural rules:
- contract crates define shape and semantic meaning only
- runtime crates implement behavior but do not redefine contract fields
- constants and enum-like semantic identifiers must be referenced from authoritative owners
- configuration values must not be embedded into contract definitions
- debug surfaces that are operational APIs must be classified explicitly as contract or non-contract

Coupling controls:
- no payload field names defined inside assembler business logic
- no duplicate timestamp semantics across layers
- no Python mirror evolves independently after Rust ownership begins

## 8. Freeze Tests
At minimum, define the following test classes.

### 8.1 Schema Parity Tests
- Rust serialization shape matches existing consumer expectations
- optional and required fields match contract inventory

### 8.2 Semantics Parity Tests
- timestamps preserve source-time meaning
- degraded markers preserve original meaning
- diagnostics presence does not regress

### 8.3 Cutover Tests
- Rust producer to existing Python consumer
- Rust producer to existing L4 consumer path
- dual-run compare on representative payload samples

## 9. Non-Negotiable Invariants
These must be treated as hard gates.
- source time is never overwritten by broadcast time
- `rust_active` continuity remains observable from L0 to L4
- `shm_stats` continuity remains observable from L0 to L4
- no silent contract field deletion
- no field rename without coordinated migration record
- no hidden type widening or narrowing

## 10. Common Failure Modes
- freezing only field names but not semantic meaning
- forgetting debug endpoints that are operationally treated as contracts
- allowing Python mirrors to evolve after Rust ownership starts
- introducing new fallback fields without inventory update

## 11. Recommended Execution Sequence
1. enumerate active contracts in `shared + L0`
2. record field inventory and semantic notes
3. classify each field as stable, transitional, or deprecated
4. assign Rust owner module for each contract
5. define compatibility mapping for current Python readers
6. add parity and drift tests
7. forbid non-reviewed contract changes during migration

## 12. Risks and Controls
Risk:
- freezing schema shape without freezing semantic ownership
Control:
- every contract must include owner mapping and timestamp semantics

Risk:
- contract keys drifting because constants ownership is not centralized
Control:
- all enum-like strings and payload keys must reference authoritative constant owners

Risk:
- debug-facing payloads omitted from freeze scope
Control:
- operationally consumed debug surfaces are included when they behave as contracts

## 13. Review and Revision
Initial draft issue found during self-review:
- The earlier version emphasized field lists, but not operational debug surfaces that behave like contracts in practice.

Revision applied:
- diagnostics and debug-facing payloads are now explicitly included when they are consumed operationally.
- timestamp semantics are now elevated as a first-class freeze artifact rather than a note.

Normative review conclusion:
- This checklist is specific enough to govern execution.
- It addresses both schema shape and semantic meaning.
- It reduces the main source of migration drift.

Landing feasibility conclusion:
- The checklist is implementable with current repository structure and should be completed before large-scale Rust runtime ownership changes.



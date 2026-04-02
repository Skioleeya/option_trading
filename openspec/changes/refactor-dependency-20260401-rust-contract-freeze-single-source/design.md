## Context

The repository already has documented contract-freeze guidance, but it is not yet represented as an OpenSpec child proposal with executable review stages. This child proposal must turn that guidance into a governed, dependency-first unit that blocks downstream drift.

## Goals

- produce an unambiguous contract-freeze execution boundary for `shared + L0`
- define single-source ownership for contract groups before implementation planning continues
- preserve source-time, diagnostics, and payload semantics across the future Rust migration

## Non-Goals

- no runtime code implementation
- no constants tuning work beyond identifying contract-owned semantic identifiers
- no downstream modular decomposition of `shared + L0`

## Controls

1. No ambiguous field meaning is allowed in the contract inventory.
2. Timestamp fields must state source-time versus broadcast-time semantics explicitly.
3. Debug-facing payloads that act as operational APIs must be classified as contract or non-contract.
4. Contract owner modules must be named before this child can close.
5. No downstream child may redefine a frozen contract without a new governed proposal.
6. Contract crates must remain high-cohesion and low-coupling: they define shape and semantic meaning only, and they must not absorb runtime orchestration concerns.
7. Contract-freeze claims must point to explicit evidence artifacts instead of relying on implied repository familiarity.

## Risk Controls

- If any contract field lacks an owner or semantic note, block closure.
- If Python mirror strategy is undefined, block closure.
- If drift-test classes are missing, block closure.
- If debug surfaces are omitted from review despite operational use, block closure.
- If contract-freeze outputs mix schema ownership with runtime behavior planning, block closure.
- If artifact contents drift from L0/L1 SOP contract statements, block closure.

## Execution Model

This child advances through three states:

1. `created`
   - proposal, design, tasks, and spec exist
   - dependency order and rollback gates are defined
2. `validated`
   - contract-freeze artifact exists
   - timestamp semantics, owner mapping, and downstream invariants are recorded
   - parent-child order and evidence references remain consistent
3. `closable`
   - downstream handoff inputs are accepted as sufficient
   - no ambiguous contract surfaces remain
   - strict validation evidence is present in session handoff

The target for this session is `validated`, not `closable`.

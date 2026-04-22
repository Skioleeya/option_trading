## Context

The Rust migration requires a single owner for contract-level identifiers and a separate owner for runtime-tunable values. Without this separation, language migration would merely copy Python hardcoding into Rust.

## Goals

- define constants and config as separate governance domains
- eliminate hardcoded thresholds, payload keys, and ad hoc environment reads from future Rust runtime planning
- preserve high cohesion and low coupling between immutable semantic owners and tunable runtime owners

## Non-Goals

- no runtime code implementation
- no direct contract schema freeze work beyond consuming the outputs of the dependency child
- no `shared + L0` modular split work in this child

## Controls

1. `constants` owns immutable semantic identifiers and fixed contract values only.
2. `config` owns tunable runtime parameters, loading, overrides, and validation only.
3. Runtime crates may consume `constants` and `config`, but may not redefine either.
4. No business logic may read environment variables directly.
5. Every tunable value must be classified as config or explicitly justified as a constant.
6. Governance claims must reference a concrete constants/config artifact rather than narrative-only statements.

## Risk Controls

- If a value is classified inconsistently across proposal, design, tasks, or spec, block closure.
- If payload keys or degraded labels are not assigned to constant owner files, block closure.
- If environment access bypasses the config boundary, block closure.
- If domain grouping degrades into a monolithic catch-all constants file, block closure.
- If upstream dependency identifiers are not consumed and classified, block closure.

## Execution Model

This child advances through three states:

1. `created`
   - proposal, design, tasks, and spec exist
   - dependency order is fixed behind the dependency child
2. `validated`
   - constants/config evidence package exists
   - owner file model, taxonomy, validation pipeline, and anti-hardcoding invariants are recorded
   - upstream dependency identifiers are consumed without contradiction
3. `closable`
   - downstream boundary child accepts the governance checklist as sufficient input
   - no ambiguous owner classification remains
   - strict validation evidence is present in session handoff

The target for this session is `validated`, not `closable`.

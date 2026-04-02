## Context

The current repository has three planning documents that define the migration direction:
- root-level shared and L0 module audit
- root-level constants and configuration design
- root-level contract freeze checklist

These documents are logically connected, but they are not yet enforced by OpenSpec as an ordered execution chain. The migration must not proceed as a free-form planning stream. It must be governed as one parent proposal with explicit child order and explicit closure criteria.

## Goals

- enforce one ordered proposal chain for Rust runtime migration governance
- require contract freeze before downstream migration planning closure
- require constants and configuration governance before implementation-oriented modular boundary planning closes
- require every child proposal to contain complete, reviewable, phase-based tasks
- require parent closure to include strict validation evidence and child evidence references

## Non-Goals

- no direct runtime code implementation in this parent proposal
- no L1, L2, L3, or app migration implementation work in this parent proposal
- no protocol schema rewrite outside the child contract-freeze proposal

## Parent Controls

1. Dependency Lock: child order is fixed as `dependency -> magic-number -> bloat -> nesting`.
2. Contract Lock: no child may redefine source-time semantics or cross-layer payload meaning.
3. Constants Lock: no child may allow runtime-tunable values to remain hardcoded without ownership classification.
4. Completeness Lock: every child tasks file must contain at least seven execution phases in addition to the required template sections.
5. Closure Lock: parent closes only after all four children pass review and strict validation evidence is recorded.
6. Evidence Lock: parent governance decisions must reference scripted validation sources instead of free-form statements.
7. State Lock: parent progress must be recorded in session notes and mirrored into context pointers before final closure.

## Risk Controls

- If any child proposal contains ambiguous scope, block review.
- If any child proposal omits anti-hardcoding or anti-coupling statements, block review.
- If child dependency order becomes inconsistent across proposal, design, tasks, and spec files, block closure.
- If parent or child lacks strict validation evidence in final handoff, block closure.
- If parent tasks claim progress without evidence links or session-state updates, block closure.

## Execution Model

The parent proposal advances through three governance states:

1. `created`
   - parent and all four children exist
   - dependency order is fixed
2. `validated`
   - parent-child cross-validation passes
   - evidence sources are recorded
   - parent tasks reflect actual governance progress
3. `closable`
   - all children satisfy their own DoD
   - parent reconciliation remains green
   - strict validation evidence is present in session handoff

The current implementation target for this session is `validated`, not `closable`.


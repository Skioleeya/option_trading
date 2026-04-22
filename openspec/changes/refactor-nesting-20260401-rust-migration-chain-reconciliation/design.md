## Context

A governed migration chain can still fail at closure time if the individual child proposals are locally complete but globally inconsistent. This child provides the final reconciliation layer so the chain closes as one coherent governance program rather than four loosely related proposal folders.

## Goals

- reconcile all parent-child references and dependency-order statements
- reconcile terminology and gate language across the chain
- define explicit archive-readiness conditions
- ensure the governance chain remains high-cohesion and low-coupling at the proposal-system level

## Non-Goals

- no runtime code implementation
- no new contract, constants, or module-boundary definitions
- no change to upstream child ordering once reconciled

## Controls

1. No parent-child reference may disagree across proposal, design, tasks, or spec files.
2. No closure gate may exist only in one file and be absent from the others.
3. No terminology drift is allowed between `contract freeze`, `constants/config governance`, `shared + L0 boundary`, and `reconciliation`.
4. Archive readiness must be explicit, not implied.
5. This child may reconcile the chain, but may not redefine upstream scope.
6. Reconciliation claims must point to a concrete chain-level evidence artifact rather than scattered local checks only.

## Risk Controls

- If child order differs anywhere in the chain, block closure.
- If one child's DoD or rollback language conflicts with the parent gate, block closure.
- If archive readiness is not explicit, block closure.
- If reconciliation introduces new scope instead of aligning existing scope, block closure.
- If parent closure preconditions are not enumerated in one place, block closure.

## Execution Model

This child advances through three states:

1. `created`
   - proposal, design, tasks, and spec exist
   - reconciliation scope is limited to alignment, not new scope
2. `validated`
   - chain-level evidence artifact exists
   - parent/child references, order, terminology, and archive-readiness language are reconciled
   - parent closure preconditions are explicit
3. `closable`
   - no unresolved chain-level inconsistency remains
   - parent can evaluate archive readiness against explicit preconditions
   - strict validation evidence is present in session handoff

The target for this session is `validated`, not `closable`.

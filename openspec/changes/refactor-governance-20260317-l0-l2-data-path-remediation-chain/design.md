## Context

Several dependency-theme child proposals for L0/L2 remediation were created and still
active, but their declared parent `refactor-governance-20260317-l0-l2-data-path-remediation-chain`
was not present in repository state. The strict OpenSpec chain gate requires this parent.

## Goals

- restore a valid parent node for the existing child proposals
- keep child execution order auditable
- allow strict validation to reason over complete governance lineage

## Non-Goals

- no modifications to runtime modules in `l0_ingest/`, `l1_compute/`, `l2_decision/`, `l3_assembly/`, `l4_ui/`, or `app/`
- no redefinition of child technical scope

## Parent Controls

1. Child order remains deterministic through each child `DEPENDENCY_ORDER`.
2. Parent closure requires all child DoD evidence and strict validation evidence.
3. Governance claims must reference scripted gates.

## Risk

Low. This is metadata restoration for governance chain integrity.

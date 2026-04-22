## ADDED Requirements

### Requirement: L1 Empty Snapshot Path Must Preserve Metadata Continuity
When L1 compute enters empty/degraded paths, output snapshot SHALL preserve incoming `extra_metadata`.

#### Scenario: Empty Chain Drops Metadata
- **WHEN** `compute()` receives an empty chain and returns empty snapshot
- **THEN** `extra_metadata` MUST still contain the incoming diagnostics payload.

### Requirement: No Semantic Rewrite of Metadata Payload
This fix SHALL pass metadata through without rewriting timestamp or rust diagnostic semantics.

#### Scenario: Metadata Keys Are Rewritten
- **WHEN** fix logic mutates or renames metadata keys
- **THEN** change MUST fail review.

### Requirement: Child Must Follow Governance Prohibitions
Implementation SHALL follow: no complex functions, no magic numbers, no complex nesting, no module coupling.

#### Scenario: Governance Prohibition Violated
- **WHEN** any prohibition is violated
- **THEN** child closure MUST be rejected.

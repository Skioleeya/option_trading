## ADDED Requirements

### Requirement: Rust Migration Governance Chain Must End With Reconciliation
The Rust runtime migration governance chain SHALL include a final reconciliation child before parent closure.

#### Scenario: Parent Attempts Closure Without Reconciliation
- **WHEN** the parent proposal closes before reconciliation verifies cross-proposal consistency and archive readiness
- **THEN** parent closure MUST be rejected.

### Requirement: Dependency Order and Gate Language Must Be Consistent Across the Chain
All parent and child files SHALL describe the same child order and the same closure-gate meaning.

#### Scenario: Cross-File Inconsistency
- **WHEN** proposal, design, tasks, or spec files disagree on child order or closure-gate meaning
- **THEN** reconciliation review MUST fail.

### Requirement: Reconciliation Must Not Introduce New Scope
The reconciliation child SHALL align existing governance artifacts but SHALL NOT introduce new upstream migration scope.

#### Scenario: Reconciliation Expands Scope
- **WHEN** the reconciliation child adds new implementation or upstream planning scope instead of reconciling existing scope
- **THEN** child closure MUST be rejected.

### Requirement: Reconciliation Must Produce a Chain-Level Evidence Package
This child SHALL produce a chain-level evidence package that records parent-child order, terminology alignment, archive-readiness conditions, and parent closure preconditions.

#### Scenario: Reconciliation Review Without Chain-Level Evidence
- **WHEN** reconciliation is reviewed without a concrete artifact that records the required chain-level alignment outputs
- **THEN** this child proposal MUST remain open.

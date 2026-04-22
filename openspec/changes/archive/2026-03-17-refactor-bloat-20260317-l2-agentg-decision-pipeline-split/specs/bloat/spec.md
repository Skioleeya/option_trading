## ADDED Requirements

### Requirement: AgentG Decision Pipeline Must Be Modularized Without Contract Drift
AgentG decision logic SHALL be split into support modules while preserving `AgentG.decide()` contract and output semantics.

#### Scenario: Refactor Changes Decision Contract
- **WHEN** the refactor changes output shape or semantic ordering of gates
- **THEN** the change MUST be rejected.

### Requirement: AgentG Core Orchestration Must Avoid Complex Monolith Function
`_decide_impl` SHALL not remain a monolithic multi-responsibility function; key sub-domains must be extracted.

#### Scenario: Monolithic Complexity Remains Unchanged
- **WHEN** complexity/length/nesting does not materially decrease
- **THEN** DoD MUST be rejected.

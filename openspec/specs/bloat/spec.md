## ADDED Requirements

### Requirement: Runtime Service Module Split
Active Options runtime service MUST be modularized so orchestration and helper logic are separated without changing external contracts.

#### Scenario: Orchestration entry remains stable
- **WHEN** downstream code imports runtime service entry points
- **THEN** exported API remains compatible
- **AND** behavior remains unchanged

### Requirement: No Coupling Expansion During Split
Refactor MUST avoid introducing new cross-layer coupling or cyclic dependencies.

#### Scenario: Dependency graph remains acyclic
- **WHEN** module split is complete
- **THEN** internal import graph remains acyclic
- **AND** boundary scan passes

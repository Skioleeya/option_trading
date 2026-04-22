## ADDED Requirements

### Requirement: Shared and L0 Migration Boundary Must Follow Upstream Governance Outputs
The `shared + L0` migration boundary SHALL consume both the contract-freeze outputs and the constants/config governance outputs before it can close.

#### Scenario: Boundary Defined Without Upstream Inputs
- **WHEN** module-boundary planning proceeds without frozen contracts or without constants/config ownership rules
- **THEN** this child proposal MUST remain open.

### Requirement: Mixed-Responsibility Modules Must Be Decomposed Before They Are Migration-Ready
A module that mixes contract, runtime, compute, or compatibility responsibilities SHALL not be treated as first-wave migration-ready.

#### Scenario: Mixed Responsibility Remains
- **WHEN** a proposed first-wave module still combines multiple ownership roles without explicit decomposition
- **THEN** child closure MUST be rejected.

### Requirement: First-Wave Scope Must Stay Bounded
The first-wave migration slice SHALL remain limited to `shared` and `L0`.

#### Scenario: Scope Creep
- **WHEN** the child proposal expands first-wave scope into `L1`, `L2`, `L3`, `app`, or `L4` without a new governed proposal
- **THEN** child review MUST fail.

### Requirement: Boundary Governance Must Produce an Evidence Package
This child SHALL produce an evidence package that records first-wave modules, exclusions, decomposition rules, validation matrix, rollback radius, and implementation entry conditions.

#### Scenario: Boundary Review Without Evidence Package
- **WHEN** the first-wave boundary is reviewed without a concrete evidence artifact that records the required migration-boundary outputs
- **THEN** this child proposal MUST remain open.

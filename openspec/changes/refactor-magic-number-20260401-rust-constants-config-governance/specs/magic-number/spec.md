## ADDED Requirements

### Requirement: Constants Governance Must Follow Contract Freeze
Constants and configuration governance SHALL consume the contract-freeze outputs before it can close.

#### Scenario: Missing Contract-Freeze Inputs
- **WHEN** semantic identifier ownership depends on contract-freeze outputs that are not yet defined
- **THEN** this child proposal MUST remain open.

### Requirement: Constants and Config Must Remain Separate Owner Domains
Immutable semantic identifiers SHALL be owned by `constants`, and tunable runtime parameters SHALL be owned by `config`.

#### Scenario: Mixed Ownership
- **WHEN** a proposal allows `constants` and `config` responsibilities to mix without explicit separation
- **THEN** child review MUST fail.

### Requirement: Direct Environment Reads Are Forbidden in Business Logic
Business logic SHALL consume validated configuration only through the config boundary.

#### Scenario: Ad Hoc Environment Access
- **WHEN** the governance model permits direct environment reads inside business or runtime logic
- **THEN** child closure MUST be rejected.

### Requirement: Constants and Config Governance Must Produce an Evidence Package
This child SHALL produce an evidence package that records owner files, taxonomy, classification examples, validation pipeline, and downstream anti-hardcoding invariants.

#### Scenario: Governance Review Without Evidence Package
- **WHEN** constants/config governance is reviewed without a concrete evidence artifact that records the required owner and validation model
- **THEN** this child proposal MUST remain open.

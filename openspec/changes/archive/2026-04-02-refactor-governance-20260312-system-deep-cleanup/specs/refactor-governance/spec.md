## ADDED Requirements

### Requirement: Deep Cleanup Must Use Parent Plus Child Proposal Governance
System deep cleanup SHALL be executed only via one parent proposal and four themed child proposals (`dependency`, `nesting`, `bloat`, `magic-number`).

#### Scenario: Implementation Starts Before Proposal Set Is Complete
- **WHEN** runtime code refactor starts before parent/child proposal files are fully created
- **THEN** the change MUST be blocked as governance non-compliant.

### Requirement: Child Execution Must Respect Dependency Order
Child proposals SHALL execute in declared dependency order and MUST NOT skip upstream gates.

#### Scenario: Out-of-Order Child Implementation
- **WHEN** `bloat` starts before `dependency` and `nesting` are validated
- **THEN** implementation MUST stop and return to dependency order.

### Requirement: Parent Closure Must Provide Quant Evidence and Strict Gate Output
Parent proposal closure SHALL include before/after quantitative metrics, test evidence, and strict validation output summary.

#### Scenario: Handoff Without Strict Evidence
- **WHEN** a handoff claims completion without `scripts/validate_session.ps1 -Strict` output summary
- **THEN** closure MUST be rejected.

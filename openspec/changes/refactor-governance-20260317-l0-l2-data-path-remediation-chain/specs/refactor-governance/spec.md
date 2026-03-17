## ADDED Requirements

### Requirement: L0-L2 Remediation Must Follow Parent-Child Governance
L0-L2 data-path remediation SHALL be executed through one governance parent proposal and ordered child proposals.

#### Scenario: Runtime Fix Starts Without Child Ordering
- **WHEN** runtime remediation is implemented before ordered child proposals are established
- **THEN** implementation MUST be blocked.

### Requirement: Governance Prohibitions Are Mandatory for All Children
All child proposals SHALL explicitly enforce these prohibitions: no complex functions, no magic numbers, no complex nesting, no module coupling.

#### Scenario: Child Omits Prohibition Clause
- **WHEN** any child proposal lacks one of the four prohibition clauses
- **THEN** child review MUST fail.

### Requirement: Parent Closure Must Contain Strict Evidence
Parent closure SHALL include strict validation command output summary and child evidence links.

#### Scenario: Missing Strict Evidence
- **WHEN** parent closure lacks `scripts/validate_session.ps1 -Strict` summary
- **THEN** parent closure MUST be rejected.

## ADDED Requirements

### Requirement: ActiveOptions Input Remediation Must Follow Parent-Child Governance
ActiveOptions input-path remediation SHALL be executed through one governance parent proposal and ordered child proposals.

#### Scenario: Runtime Work Starts Without Parent-Child Chain
- **WHEN** implementation starts before parent-child governance chain is established
- **THEN** implementation MUST be blocked.

### Requirement: Governance Prohibitions Are Mandatory for Children
All children under this parent SHALL explicitly include these prohibitions: no complex functions, no magic numbers, no complex nesting, no module coupling.

#### Scenario: Child Omits Mandatory Prohibitions
- **WHEN** a child proposal misses any mandatory prohibition
- **THEN** child review MUST fail.

### Requirement: Parent Closure Must Contain Strict Evidence
Parent closure SHALL include strict validation summary and child evidence references.

#### Scenario: Missing Strict Validation Evidence
- **WHEN** parent closure lacks `scripts/validate_session.ps1 -Strict` evidence
- **THEN** parent closure MUST be rejected.

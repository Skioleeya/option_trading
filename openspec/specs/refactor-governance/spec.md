## ADDED Requirements

### Requirement: Active Options Volume Contract Refactor Must Use Parent-Child Governance
Any runtime remediation targeting `volume/current_volume/turnover` continuity SHALL be executed under one `refactor-governance-*` parent proposal with ordered child proposal(s).

#### Scenario: Runtime Fix Starts Without Parent Governance
- **WHEN** a runtime change starts before parent + child proposal set is complete
- **THEN** implementation MUST be blocked as governance non-compliant.

### Requirement: Governance Prohibitions Must Be Enforced
This governance chain SHALL enforce all prohibitions: no module coupling, no complex nesting, no complex functions, and no garbage code.

#### Scenario: Prohibition Violation Detected
- **WHEN** any implementation introduces coupling, deep nesting, oversized multi-responsibility function, or low-quality temporary code
- **THEN** proposal closure MUST be rejected.

### Requirement: Parent Closure Must Include Quant Evidence
Parent closure SHALL provide before/after metrics for log noise and contract continuity, with strict gate output summary.

#### Scenario: Missing Quant or Strict Evidence
- **WHEN** closure lacks quant comparison or strict validation evidence
- **THEN** parent completion MUST be rejected.

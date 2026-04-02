## ADDED Requirements

### Requirement: L0-L2 Remediation Governance Chain Must Have a Parent Record
All active child remediation proposals under this chain SHALL reference an existing parent change record.

#### Scenario: Child Proposals Referencing Missing Parent
- **WHEN** OpenSpec chain validation scans child proposals
- **THEN** the referenced parent record MUST exist in `openspec/changes/`.

### Requirement: Parent Closure Depends on Child Completion Evidence
The governance parent SHALL remain open until all child proposals provide completion and strict-validation evidence.

#### Scenario: Attempted Parent Closure Without Child Evidence
- **WHEN** parent closure is requested but required child evidence is incomplete
- **THEN** closure MUST be rejected.

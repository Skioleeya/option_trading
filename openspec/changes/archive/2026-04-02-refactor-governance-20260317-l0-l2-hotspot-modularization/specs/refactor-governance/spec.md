## ADDED Requirements

### Requirement: High-Coupling Modularization Must Use Parent-Child Governance
Any modular split targeting high-coupling runtime files SHALL be orchestrated via one `refactor-governance-*` parent proposal and ordered child proposals.

#### Scenario: Runtime Split Starts Without Parent Governance
- **WHEN** runtime modularization work starts before parent + child proposal set is complete
- **THEN** implementation MUST be blocked as governance non-compliant.

### Requirement: Target Runtime Files Must Respect Single-Responsibility and File-Length Cap
Target runtime files (`option_chain_builder.py`, `extractors.py`) SHALL be split so each resulting file has a single dominant responsibility and SHALL NOT exceed 450 LOC.

#### Scenario: Oversized File Remains After Refactor
- **WHEN** a target file remains over 450 LOC after child proposal completion
- **THEN** parent proposal closure MUST be rejected.

### Requirement: Parent Closure Must Include Quant Evidence and Strict Gate Output
Parent proposal closure SHALL include before/after metrics, child completion evidence, and strict validation output summary.

#### Scenario: Missing Strict Evidence in Parent Closure
- **WHEN** closure claims completion without `scripts/validate_session.ps1 -Strict` output summary
- **THEN** closure MUST be rejected.

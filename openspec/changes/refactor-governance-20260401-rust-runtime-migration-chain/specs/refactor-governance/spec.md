## ADDED Requirements

### Requirement: Rust Runtime Migration Governance Must Follow One Ordered Parent-Child Chain
Rust runtime migration governance SHALL be executed through one parent proposal and four ordered child proposals.

#### Scenario: Work Starts Without Ordered Governance Chain
- **WHEN** migration planning or implementation is advanced without the full parent-child chain being created and linked
- **THEN** proposal review and closure MUST be blocked.

### Requirement: Child Order Is Fixed
The governance chain SHALL enforce child order `refactor-dependency-20260401-rust-contract-freeze-single-source -> refactor-magic-number-20260401-rust-constants-config-governance -> refactor-bloat-20260401-rust-shared-l0-migration-boundary -> refactor-nesting-20260401-rust-migration-chain-reconciliation`.

#### Scenario: Out-of-Order Child Progression
- **WHEN** a downstream child is treated as complete before its predecessor is reviewed and accepted
- **THEN** parent closure MUST be rejected.

### Requirement: Parent Closure Requires Complete Child Evidence
Parent closure SHALL include strict validation evidence and explicit child evidence references.

#### Scenario: Missing Strict Evidence or Child References
- **WHEN** the parent closes without `scripts/validate_session.ps1 -Strict` evidence or without child reference completeness
- **THEN** parent closure MUST be rejected.

### Requirement: Governance Evidence Must Reference Scripted Sources of Truth
The governance chain SHALL reference scripted validation and quality-gate sources of truth rather than free-form review claims.

#### Scenario: Governance Claim Without Scripted Evidence Source
- **WHEN** a parent or child proposal claims readiness without pointing to the scripted validation source for strict validation, OpenSpec chain validation, or quality thresholds
- **THEN** governance review MUST reject the claim as incomplete.


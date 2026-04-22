## ADDED Requirements

### Requirement: Function and Class Size Must Respect Thresholds
Target code SHALL satisfy function length <= 80 LOC and class length <= 400 LOC.

#### Scenario: Oversized Function Remains
- **WHEN** a targeted function remains longer than 80 LOC after refactor
- **THEN** closure MUST be blocked until split is complete.

### Requirement: Bloat Refactor Must Keep Contract Compatibility
Service split SHALL preserve existing external contracts and runtime payload semantics.

#### Scenario: Split Changes Payload Field Semantics
- **WHEN** a refactor changes output contract fields without migration
- **THEN** the change MUST fail verification.

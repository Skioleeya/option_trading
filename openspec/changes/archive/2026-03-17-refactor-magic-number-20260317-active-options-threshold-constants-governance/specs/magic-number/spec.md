## ADDED Requirements

### Requirement: Govern Threshold Magic Numbers
Active Options threshold literals MUST be governed through named constants to improve auditability and reduce drift risk.

#### Scenario: Literal replacement keeps behavior stable
- **WHEN** threshold literals are replaced with constants
- **THEN** runtime default behavior remains unchanged
- **AND** tests confirm no regression

### Requirement: Keep Constant Ownership Clear
Threshold constants MUST have a single authoritative owner module in scope.

#### Scenario: No duplicated threshold source
- **WHEN** constants are introduced
- **THEN** duplicate threshold definitions are removed
- **AND** call sites reference the same source

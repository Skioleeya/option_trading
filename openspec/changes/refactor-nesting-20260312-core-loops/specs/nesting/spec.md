## ADDED Requirements

### Requirement: Nesting Depth Must Stay Within Institutional Threshold
Target functions SHALL keep max nesting depth <= 3, and hot path functions <= 2.

#### Scenario: Hot Path Function Exceeds Depth
- **WHEN** a designated hot path function has nesting depth 3 or higher
- **THEN** the function MUST be refactored before closure.

### Requirement: Control-Flow Refactor Must Preserve Behavior
Nesting reduction SHALL be structural-only and MUST NOT change business semantics.

#### Scenario: Refactor Alters Signal Outcome
- **WHEN** regression tests show changed output for same input
- **THEN** the refactor MUST be rejected and corrected.

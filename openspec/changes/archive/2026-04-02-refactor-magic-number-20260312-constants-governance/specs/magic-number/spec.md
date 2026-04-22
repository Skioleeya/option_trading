## ADDED Requirements

### Requirement: Business Magic Numbers Must Be Governed by Named Constants
Business thresholds and strategy numbers SHALL be defined in named constants or config surfaces, excluding structural literals `0/1/-1`.

#### Scenario: Business Threshold Hardcoded in Hot Path
- **WHEN** a hot-path branch compares against raw numeric thresholds
- **THEN** those thresholds MUST be extracted to named constants before closure.

### Requirement: Constant Governance Must Preserve Runtime Semantics
Magic-number cleanup SHALL keep runtime behavior unchanged unless explicitly approved in proposal scope.

#### Scenario: Constant Extraction Changes Signal Trigger
- **WHEN** refactor changes signal trigger behavior
- **THEN** verification MUST fail and require rollback or explicit contract update.

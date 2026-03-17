## ADDED Requirements

### Requirement: L1 Arrow Contract Must Preserve Active Options Volume Fields
The L1 Arrow contract SHALL preserve `volume`, `current_volume`, and `turnover` continuity for downstream Active Options processing.

#### Scenario: Arrow Output Drops `current_volume` or `turnover`
- **WHEN** L1 output is transformed into Arrow payload
- **THEN** `current_volume` and `turnover` MUST remain available to downstream consumers.

### Requirement: Housekeeping Normalization Must Remain Deterministic
Housekeeping normalization SHALL apply deterministic fallback from `current_volume` to `volume` when `volume` is unavailable or invalid.

#### Scenario: Low-activity Snapshot Has `volume=0` but `current_volume>0`
- **WHEN** housekeeping normalizes chain rows
- **THEN** normalized row MUST carry usable volume semantics for Active Options filtering.

### Requirement: Dependency Fix Must Respect Governance Prohibitions
Implementation SHALL enforce no module coupling, no complex nesting, no complex function, and no garbage code.

#### Scenario: Governance Violation During Dependency Refactor
- **WHEN** any prohibition is violated
- **THEN** proposal closure MUST be rejected.

## ADDED Requirements

### Requirement: L0 Fallback Snapshots Must Carry Runtime Diagnostics
Uninitialized and error snapshots SHALL include `rust_active`, `rust_shm_path`, and `shm_stats` keys.

#### Scenario: Fallback Snapshot Missing Diagnostics Keys
- **WHEN** fallback snapshot omits runtime diagnostic keys
- **THEN** change MUST fail verification.

### Requirement: Fallback Status Labels Must Be Explicit
Fallback snapshots SHALL use explicit status labels to distinguish `UNINITIALIZED` and `ERROR` states.

#### Scenario: Status Ambiguous in Fallback Output
- **WHEN** fallback status cannot distinguish initialization vs runtime error
- **THEN** closure MUST be rejected.

### Requirement: Child Must Follow Governance Prohibitions
Implementation SHALL follow: no complex functions, no magic numbers, no complex nesting, no module coupling.

#### Scenario: Governance Prohibition Violated
- **WHEN** any prohibition is violated
- **THEN** child closure MUST be rejected.

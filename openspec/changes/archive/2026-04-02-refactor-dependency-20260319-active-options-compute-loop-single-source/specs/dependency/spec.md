## ADDED Requirements

### Requirement: ActiveOptions Input Must Be Produced by ComputeLoop as Single Source
ActiveOptions runtime input SHALL be produced by ComputeLoop and published through shared state as the single source for Housekeeping consumption.

#### Scenario: Housekeeping Performs Cross-Source Arbitration
- **WHEN** Housekeeping attempts to arbitrate between L1/L0 sources directly
- **THEN** verification MUST fail.

### Requirement: Housekeeping Must Be Consumer-Only for ActiveOptions Input
Housekeeping SHALL consume published input snapshots only and MUST NOT fetch alternate runtime sources for ActiveOptions path.

#### Scenario: Consumer Path Reintroduces Fetch Fallback
- **WHEN** Housekeeping contains fetch-based source fallback logic in ActiveOptions path
- **THEN** change MUST be rejected.

### Requirement: Input Channel Diagnostics Must Be Observable
The runtime diagnostics surface SHALL include ActiveOptions input channel validity, age, and source version for root-cause triage.

#### Scenario: Input Channel Has No Diagnostics
- **WHEN** diagnostics endpoint lacks input channel visibility
- **THEN** verification MUST fail.

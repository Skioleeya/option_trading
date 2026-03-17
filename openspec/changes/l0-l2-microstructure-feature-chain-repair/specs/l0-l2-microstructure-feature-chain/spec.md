## ADDED Requirements

### Requirement: Rust SHM Events MUST Drive L1 Microstructure Callbacks
The runtime SHALL ensure Rust SHM-origin depth/trade events drive L1 microstructure callback update paths used for VPIN/BBO state evolution.

#### Scenario: Depth Event Updates BBO Path
- **WHEN** a Rust SHM event is classified as depth and contains valid top-of-book data
- **THEN** the runtime SHALL invoke the depth callback path used by L1 BBO updates
- **AND** `bbo_imbalance_ewma` SHALL be eligible to move away from static zero under non-neutral book pressure

#### Scenario: Trade Event Updates VPIN Path
- **WHEN** a Rust SHM event is classified as trade with valid trade payload
- **THEN** the runtime SHALL invoke the trade callback path used by L1 VPIN updates
- **AND** `vpin_composite` SHALL be eligible to evolve away from static zero under directional flow

### Requirement: Peak Impact Extraction MUST Support RecordBatch Runtime Path
The L2 feature extraction path SHALL compute `peak_impact`/`max_impact` correctly for both legacy dict rows and Arrow `RecordBatch` rows.

#### Scenario: RecordBatch Chain With Computed Gamma
- **WHEN** L2 receives a runtime `RecordBatch` chain containing turnover/volume and computed gamma columns
- **THEN** `peak_impact` SHALL be computed from non-null available flow/gamma fields
- **AND** `max_impact` in decision output/audit SHALL not default to zero when valid inputs exist

#### Scenario: Legacy Dict Chain Compatibility
- **WHEN** L2 receives legacy dict-style chain rows
- **THEN** legacy extraction behavior SHALL remain compatible without schema break

### Requirement: Turnover Velocity MUST Use WS-First Controlled Fallback
`turnover_velocity` SHALL follow WS-authoritative semantics with explicit REST fallback when WS turnover data is unavailable.

#### Scenario: WS Turnover Available
- **WHEN** WS turnover fields are present and valid
- **THEN** `turnover_velocity` SHALL be derived from WS-aligned turnover progression
- **AND** REST fallback SHALL NOT override WS-derived values

#### Scenario: WS Turnover Missing, REST Fields Available
- **WHEN** WS turnover is unavailable but REST turnover/current_volume is available in L0-preserved contract fields
- **THEN** runtime SHALL use bounded REST fallback to avoid prolonged forced-zero velocity
- **AND** fallback usage SHALL be diagnosable via explicit telemetry/log markers


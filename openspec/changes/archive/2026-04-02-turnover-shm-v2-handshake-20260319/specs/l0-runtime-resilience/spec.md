## ADDED Requirements

### Requirement: SHM Push Event Version Handshake

L0 Rust SHM producer MUST publish version metadata in header reserved bytes while keeping `head@0`, `tail@64`, `buffer@128` unchanged.

#### Scenario: Producer writes v2 metadata
- **GIVEN** Rust runtime creates or opens SHM
- **WHEN** producer initializes control pointers
- **THEN** it writes `magic/schema_version/event_size` into header metadata offsets

### Requirement: Turnover Flow Fields in Push Event

L0 Rust push event MUST expose `current_volume` and `turnover` for quote events to Python bridge.

#### Scenario: Quote push event
- **GIVEN** quote push has turnover/current-volume
- **WHEN** event is serialized to SHM
- **THEN** Python bridge decodes non-empty `current_volume/turnover`

### Requirement: Python Backward Compatibility

Python RustBridge MUST decode both v2 and legacy v1 SHM layouts.

#### Scenario: Legacy producer without metadata
- **GIVEN** SHM header has no valid metadata
- **WHEN** Python bridge connects
- **THEN** bridge falls back to legacy v1 layout and emits `None` for v2-only fields

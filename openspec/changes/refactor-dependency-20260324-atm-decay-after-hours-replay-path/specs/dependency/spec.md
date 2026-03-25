## ADDED Requirements

### Requirement: ATM Decay Must Support Test-Only After-Hours Replay Through Tracker Boundary
When after-hours replay is explicitly enabled, ATM decay SHALL be prepared and replayed through `AtmDecayTracker` public behavior instead of app-layer private storage access.

#### Scenario: App Layer Touches Tracker Private Storage
- **WHEN** replay logic requires `app` or loops to call tracker/storage private members directly
- **THEN** verification MUST fail.

### Requirement: After-Hours Replay Must Reuse Existing History and WS Contracts
Replay SHALL populate the existing ATM history store for the active trade date and SHALL continue to publish the existing `atm` payload contract on `/ws/dashboard`.

#### Scenario: Replay Introduces a Separate Frontend Contract
- **WHEN** replay requires a replay-only API route or frontend wire shape
- **THEN** change MUST be rejected.

### Requirement: Replay Window Must Exclude Flat Curve Segments
Replay source selection SHALL reject flat or platformed windows, including windows whose first or last point is a `0/0/0` flat row.

#### Scenario: Replay Seeds a Flat Window
- **WHEN** the selected replay window is flat or edge-flat
- **THEN** verification MUST fail.

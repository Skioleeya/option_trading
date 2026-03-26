## ADDED Requirements

### Requirement: L3 Must Emit Visual Payload Summary Logs
L3 runtime SHALL emit a structured payload summary log that makes Depth Profile and ATM chart transmission status explicit.

#### Scenario: Payload Built On A Compute Tick
- **WHEN** L3 completes a payload build from live snapshot data
- **THEN** the runtime MUST emit a `[L3-PAYLOAD]` log
- **AND** the log MUST include Depth Profile row count and key strikes
- **AND** the log MUST include ATM status plus `straddle/call/put` values when present

### Requirement: ATM Debug Status Must Distinguish Outside-RTH From Missing Live Payload
ATM debug logs SHALL not conflate after-hours suppression with transport failure.

#### Scenario: After-Hours ATM Update
- **WHEN** the system is outside regular trading hours and ATM payload is absent
- **THEN** the payload summary MUST mark ATM as `MISSING_OUTSIDE_RTH`
- **AND** operators MUST be able to distinguish this case from an in-hours missing payload

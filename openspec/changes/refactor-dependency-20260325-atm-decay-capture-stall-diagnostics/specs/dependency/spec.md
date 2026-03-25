## ADDED Requirements

### Requirement: ATM Opening Capture Failures Must Emit Periodic Stall Forensics
When same-day ATM opening capture keeps failing after an actual capture attempt, the tracker SHALL emit throttled INFO-level forensic logs that summarize the capture inputs.

#### Scenario: Repeated Update Capture Failures Reach The Logging Threshold
- **WHEN** `update()` keeps attempting same-day fresh capture and still has no active anchor
- **AND** the capture failure streak reaches the configured threshold
- **THEN** the tracker SHALL emit one INFO log containing the failure count, capture context, current spot, total chain size, 0DTE contract count, and integer-strike count
- **AND** the tracker SHALL continue trying future captures without changing ATM decay output contracts

### Requirement: Successful Or Reset Transitions Must Clear Capture Failure Streak
The tracker SHALL clear the capture failure streak whenever the capture lifecycle enters a new clean phase.

#### Scenario: Successful Anchor Lock Resets Capture Failure Diagnostics
- **WHEN** same-day capture eventually succeeds and persists a new anchor
- **THEN** the tracker SHALL reset the capture failure streak to `0`
- **AND** subsequent stall logs SHALL count from the new post-lock lifecycle rather than the prior failure window

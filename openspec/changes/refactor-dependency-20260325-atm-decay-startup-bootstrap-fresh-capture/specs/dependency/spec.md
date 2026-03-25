## ADDED Requirements

### Requirement: Startup Bootstrap Must Not Be Blocked By Pending Restore Anchors
When intraday startup bootstrap runs while a pending restore anchor exists, the tracker SHALL first evaluate that pending anchor via strict restore/discard logic and SHALL continue to fresh capture if the pending anchor is rejected.

#### Scenario: Deferred Restore Anchor Fails Distance Validation At Startup
- **WHEN** startup bootstrap sees a pending same-day anchor and the current spot invalidates it by distance check
- **THEN** the tracker SHALL clear the pending restore anchor
- **AND** the same bootstrap attempt SHALL continue to capture a fresh same-day ATM anchor from the current chain snapshot
- **AND** startup relock SHALL NOT wait for a later manual restart or external reset.

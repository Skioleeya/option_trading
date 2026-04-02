## ADDED Requirements

### Requirement: Broken Same-Day ATM Anchors Must Self-Invalidate
When the active ATM anchor cannot produce valid call/put decay inputs for a bounded number of consecutive runtime ticks, the tracker SHALL invalidate the current same-day anchor and allow the runtime to capture a replacement anchor.

#### Scenario: Consecutive Leg Starvation
- **WHEN** the active anchor repeatedly yields `raw_pct_unavailable` because one or both anchor legs are non-positive or missing
- **THEN** the tracker SHALL clear the in-memory anchor
- **AND** the persisted same-day anchor SHALL be removed
- **AND** subsequent market-hour ticks SHALL be allowed to capture a new ATM anchor.

### Requirement: Mandatory Anchor Symbols Must Clear When Anchor Clears
The housekeeping loop SHALL synchronize mandatory anchor symbols with the current anchor set, including the empty-set case.

#### Scenario: Anchor Invalidated Mid-Session
- **WHEN** the ATM anchor becomes invalid and exposes no anchor symbols
- **THEN** the runtime SHALL publish an empty mandatory-symbol set
- **AND** stale anchor legs SHALL NOT remain pinned solely because of prior mandatory-symbol state.

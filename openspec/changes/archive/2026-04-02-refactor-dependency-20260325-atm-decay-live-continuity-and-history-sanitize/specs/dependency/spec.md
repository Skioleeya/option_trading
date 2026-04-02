## ADDED Requirements

### Requirement: Duplicate Snapshot Ticks Must Preserve ATM Live Continuity
When the compute loop deduplicates an unchanged `snapshot_version`, it SHALL still allow ATM decay live sampling to advance through the existing `/ws/dashboard` `atm` payload contract.

#### Scenario: Duplicate Snapshot Tick Produces New ATM Sample
- **WHEN** `snapshot_version` is unchanged but `AtmDecayTracker` yields a new ATM item
- **THEN** the backend SHALL publish that ATM item through the existing L3/L4 payload path without re-running L1/L2.

### Requirement: ATM Decay History Must Be Sanitized Before Exposure or Restore
ATM decay history SHALL be filtered to the requested trade date, sorted by timestamp ascending, deduplicated by normalized timestamp, and SHALL reject future-in-session timestamps before restore or API exposure.

#### Scenario: Cold History Contains Future Or Out-of-Order Rows
- **WHEN** cold ATM history contains future timestamps, duplicate timestamps, or out-of-order rows
- **THEN** Redis restore and `/api/atm-decay/history` SHALL expose only the sanitized monotonic sequence.

### Requirement: ATM Repair Must Preserve Existing Frontend Contracts
The repair SHALL keep `/api/atm-decay/history` and `/ws/dashboard` wire shapes unchanged.

#### Scenario: Repair Requires New Frontend-Specific Contract
- **WHEN** the implementation introduces a replay-only or live-only frontend route or wire shape
- **THEN** the change MUST be rejected.

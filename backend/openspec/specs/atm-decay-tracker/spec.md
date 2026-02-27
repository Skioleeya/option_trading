# atm-decay-tracker Specification

## Purpose
TBD - created by archiving change atm-decay-persistence. Update Purpose after archive.
## Requirements
### Requirement: 9:30 AM ET Anchoring
The system SHALL capture the price of the At-The-Money (ATM) option strike exactly at or immediately after 9:30 AM ET on each trading day.

#### Scenario: Market opens and ATM strike is determined
- **WHEN** the system processes the first option chain update at or after 9:30 AM ET
- **THEN** it identifies the ATM strike based on the nearest whole number to the SPY spot price
- **THEN** it extracts the current Ask/Mid prices for the Call and Put at that strike
- **THEN** it calculates the initial Straddle price (Call + Put)

### Requirement: Anchor Persistence
The system SHALL persist the initial 9:30 AM ATM option prices to ensure continuity across service restarts and providing a baseline for calculation.

#### Scenario: Anchor data is saved
- **WHEN** the 9:30 AM ET anchor prices are successfully captured
- **THEN** the system saves the `strike`, `call_price`, `put_price`, and `timestamp` to a Redis key (e.g., `app:opening_atm:{YYYYMMDD}`)
- **THEN** the system writes a JSON backup to the configured `config.opening_atm_cold_storage_root` directory

#### Scenario: Service restarts mid-day
- **WHEN** the backend service starts up
- **THEN** it attempts to load the current day's anchor from Redis, falling back to the local JSON file
- **THEN** if found, it uses this restored state as the baseline for the remainder of the day

### Requirement: Percentage Decay Calculation
The system SHALL calculate the percentage change of the anchored Call, Put, and Straddle premiums relative to their initial 9:30 AM prices.

#### Scenario: Generating the real-time decay metrics
- **WHEN** a new option chain snapshot is received
- **THEN** the system retrieves the current prices for the anchored ATM strike
- **THEN** it calculates the percentage change for the Call: `(Current Call - Anchor Call) / Anchor Call`
- **THEN** it calculates the percentage change for the Put: `(Current Put - Anchor Put) / Anchor Put`
- **THEN** it calculates the percentage change for the Straddle: `(Current Straddle - Anchor Straddle) / Anchor Straddle`
- **THEN** it makes these values available to the `SnapshotBuilder`

### Requirement: Time-Series History Tracking
The system SHALL maintain a historical record of the calculated decay percentages throughout the trading day to support frontend full-fetch mechanisms upon reconnection.

#### Scenario: Storing real-time ticks
- **WHEN** the real-time decay metrics are successfully calculated
- **THEN** the system appends a JSON payload containing the `timestamp`, `call_pct`, `put_pct`, and `straddle_pct` to a Redis Time-Series list/stream
- **THEN** this data is made available over a standard REST API endpoint (`GET /api/atm-decay/history`) for frontend clients doing a full fetch.


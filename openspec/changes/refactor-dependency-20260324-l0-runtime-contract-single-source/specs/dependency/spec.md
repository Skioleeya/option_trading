## ADDED Requirements

### Requirement: L0 Runtime Subscription State Must Reconcile to the Active Session
`L0QuoteRuntime.subscribe()` SHALL apply the full desired symbol set to the active runtime session rather than only updating Python-side bookkeeping.

#### Scenario: Subscription set changes after Rust runtime start
- **WHEN** the runtime is already started and a new desired symbol set is provided
- **THEN** the active session MUST reconcile to that full set before `subscribe()` returns
- **AND** diagnostics MUST expose both `desired_symbols` and `applied_symbols`.

### Requirement: L0 Field Normalization Must Have One Source Of Truth
IV/OI normalization used by sync, pollers, and REST replay SHALL be delegated to one shared normalization implementation.

#### Scenario: Tier poller and IV sync parse the same calc-index row
- **WHEN** a calc-index row contains `implied_volatility_decimal`, legacy percent IV, or nested OI aliases
- **THEN** each L0 consumer MUST derive the same normalized values from the shared parser
- **AND** L0 runtime modules MUST NOT keep duplicated parsing branches for those fields.

### Requirement: L0 Snapshot Time Semantics Must Bind To Source Update Time
The L0 snapshot contract SHALL bind `as_of/as_of_utc` to the latest successful L0 source update rather than the projection invocation time.

#### Scenario: Snapshot payload is projected after state already contains source data
- **WHEN** `fetch_snapshot()` or an error fallback payload is built
- **THEN** `as_of/as_of_utc` MUST reflect the latest known source update time
- **AND** legacy compute fallback fields such as `aggregate_greeks` and `ttm_seconds` MUST NOT appear in the payload.

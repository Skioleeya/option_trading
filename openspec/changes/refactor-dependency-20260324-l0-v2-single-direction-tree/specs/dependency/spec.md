## ADDED Requirements

### Requirement: L0 Main Runtime Path Must Not Import L1 Runtime Modules
The production L0 ingest entrypoint SHALL execute without importing `l1_compute` runtime or analysis modules.

#### Scenario: App boots through L0 V2 facade
- **WHEN** app wiring constructs the primary L0 builder
- **THEN** the builder implementation MUST come from `l0_ingest/v2`
- **AND** the L0 runtime path MUST NOT import `l1_compute`.

### Requirement: L0 Snapshot Contract Must Exclude Legacy Compute Fallback Fields
The L0 snapshot contract SHALL contain raw ingest data, diagnostics, and optional Arrow pass-through only.

#### Scenario: L0 snapshot projection occurs
- **WHEN** `fetch_snapshot()` returns an L0 payload
- **THEN** the payload MUST include `spot`, `chain`, `version`, `as_of_utc`, `rust_active`, and `shm_stats`
- **AND** the payload MUST NOT include legacy compute fallback fields such as `aggregate_greeks` or `ttm_seconds`.

### Requirement: Shared Neutral Modules Must Own Cross-Layer Arrow and SHM Contracts
Cross-layer reusable Arrow and SHM bridge logic SHALL reside in shared neutral modules rather than L0 or L1 concrete runtime packages.

#### Scenario: L0 and L1 consume Arrow/SHM helper logic
- **WHEN** Arrow schema or Rust SHM bridge helpers are needed by multiple layers
- **THEN** they MUST be imported from `shared/*` neutral modules
- **AND** neither L0 nor L1 may become the other layer's implementation dependency.

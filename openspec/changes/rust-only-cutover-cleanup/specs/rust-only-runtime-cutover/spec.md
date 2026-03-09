## ADDED Requirements

### Requirement: Rust-Only Startup Path
Application startup SHALL NOT pre-initialize Python `QuoteContext` in the default runtime mode.

#### Scenario: Default Startup
- **WHEN** backend starts with default config
- **THEN** startup SHALL construct L0 runtime through rust-only path without `primary_ctx` injection.

### Requirement: Degraded Broadcast Continuity
When Rust ingest is unavailable, system SHALL continue L4 broadcast with explicit diagnostics and empty chain payload.

#### Scenario: Rust Path Unavailable
- **WHEN** shared-memory Rust path is disconnected
- **THEN** payload SHALL continue with `rust_active=false`, valid diagnostics, and no stale frozen chain replay.


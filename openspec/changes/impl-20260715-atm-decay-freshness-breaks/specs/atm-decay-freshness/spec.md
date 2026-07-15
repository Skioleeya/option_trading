# atm-decay-freshness

## ADDED Requirements

### Requirement: ATM source freshness must gate ordinary samples
ATM decay must treat L0 source freshness as an input contract. When source age or source gap exceeds 10 seconds, the system must not publish a normal continuous ATM sample. The first valid sample after a stale period must carry `stale_recovery=true`.

### Requirement: ATM payload must expose freshness provenance
ATM decay payloads and history rows must preserve `source_timestamp`, `source_gap_ms`, `stale_recovery`, and `leg_freshness` so L4 and diagnostics can distinguish normal samples from recovery/break samples.

### Requirement: CALL/PUT legs must share freshness
ATM raw pct calculation must reject CALL/PUT legs that are missing, stale, or from different freshness windows. Rejected samples must not be written as ordinary chart points.

### Requirement: L4 ATM chart must break stale or long-gap segments
The L4 ATM chart must insert whitespace before a `stale_recovery` point and before adjacent renderable points whose timestamp gap exceeds 30 seconds.

### Requirement: roll-anchor marker must survive opening zero suppression
When an anchor roll produces an opening all-zero ATM tick that is suppressed, the pending `strike_changed` marker must remain set until the next published sample.

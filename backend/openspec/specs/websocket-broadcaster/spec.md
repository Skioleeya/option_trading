# websocket-broadcaster Specification

## Purpose
TBD - created by archiving change atm-decay-persistence. Update Purpose after archive.
## Requirements
### Requirement: WebSocket Payload Structure
The SnapshotBuilder SHALL include the `atm` decay metrics object within the `agent_g.data.ui_state` dictionary for WebSocket broadcasting.

**Reason**: To support the new ATM Decay visual component (`AtmDecayOverlay.tsx`) on the frontend, the WebSocket payload must include the calculated decay percentages.
**Migration**: The `SnapshotBuilder` must be updated to inject an `atm` object into `agent_g.data.ui_state`.

#### Scenario: Injecting ATM Decay into Snapshot
- **WHEN** the `SnapshotBuilder` constructs the final payload for broadcast
- **THEN** it retrieves the calculated decay metrics from the `AtmDecayTracker` (or equivalent service)
- **THEN** it adds the `atm` object to the `ui_state` dictionary with the following structure:
  ```json
  "atm": {
    "strike": <float>,
    "locked_at": "<string HH:MM:SS>",
    "call_pct": <float>,
    "put_pct": <float>,
    "straddle_pct": <float>
  }
  ```
- **THEN** if the anchor is not yet set (e.g., before 9:30 AM), it omits the `atm` object or sends `null` values.
- **THEN** front-end clients use this payload solely as an **incremental tick update** appended to their existing series previously acquired via Full Fetch.


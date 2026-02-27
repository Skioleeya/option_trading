# System Architecture

## Overview
The ATM Decay Persistence system introduces a reliable anchoring mechanism to track 0DTE options premium decay (Theta/Vega drain) relative to the 9:30 AM ET market open. 

This requires solving two main problems:
1. **Time-Aware Anchoring**: Capturing the exact At-The-Money (ATM) strike and its Call/Put prices at exactly 9:30 AM ET (or the first available data point thereafter).
2. **Stateful Calculation**: Comparing real-time option chain streams against this static anchor throughout the trading day to calculate percentage changes, regardless of backend restarts.

## Components Breakdown

### 1. AtmDecayTracker (New Service)
A dedicated state manager responsible for:
- Detecting if the current time crosses or is past 9:30 AM ET.
- Identifying the ATM strike based on the current underlying spot price.
- Extracting the Ask (or Mid) prices for the Call and Put at that strike.
- Persisting this anchor data to Redis (`opening_atm` key).
- Loading the anchor on backend startup if it already exists for the current trading day.

### 2. SnapshotBuilder (Modified)
The existing `SnapshotBuilder` will be updated to:
- Accept or retrieve the `opening_atm` anchor state.
- Locate the *same* strike in the real-time option chain.
- Calculate the percentage change: `(Current Price - Anchor Price) / Anchor Price`.
- Populate the `ui_state.atm` object in the payload with `call_pct`, `put_pct`, and `straddle_pct` (Call + Put combined).

### 3. Time-Series History Manager (New)
To support frontend chart rendering upon connection/reconnection:
- Appends the calculated `ui_state.atm` data points to a time-series list at regular intervals (e.g., every minute or every snapshot).
- Provides a fast retrieval mechanism for the frontend to perform a **Full Fetch (全量拉取)** of the day's history.

## Data Storage

### Redis (Primary)
- **Key 1 (Anchor)**: `app:opening_atm:{YYYYMMDD}` (Hash or JSON string) - Stores the 9:30 AM baseline.
  - `strike`: Float (e.g., 695.00)
  - `call_price`: Float
  - `put_price`: Float
  - `timestamp`: ISO String
- **Key 2 (Time-Series History)**: `app:atm_decay_series:{YYYYMMDD}` (List or Stream) - Stores the historical ticks.
  - Appends JSON array: `{"timestamp": "...", "call_pct": ..., "put_pct": ..., "straddle_pct": ...}`
- **TTL**: End of trading day + 12 hours.

### File Storage (Fallback/Audit)
- **Path**: `backend/data/opening_atm/atm_{YYYYMMDD}.json`
- Used to recover state if Redis is flushed mid-day and to provide daily historical audit trails.

## API Design & Sync Mechanism

To guarantee robust data delivery across network drops and page refreshes, the system adopts a **Full Fetch + Incremental Update (全量拉取与增量更新结合)** pattern:

### 1. Full Fetch (REST API)
- **Endpoint**: `GET /api/atm-decay/history`
- **Response**: Returns the entire `app:atm_decay_series:{YYYYMMDD}` array.
- **Trigger**: Called by the frontend `AtmDecayOverlay` immediately upon mounting or upon detecting a WebSocket reconnection.

### 2. Incremental Updates (WebSocket)
- **Endpoint**: Existing `/ws/dashboard` payload stream.
- **Payload injected**:
```json
{
  "ui_state": {
    "atm": {
      "strike": 695.0,
      "locked_at": "09:30:00",
      "call_pct": -0.292,
      "put_pct": -0.211,
      "straddle_pct": -0.252
    }
  }
}
```
- **Trigger**: Once the frontend has executed a Full Fetch, it subscribes to this incremental tick data to push new points onto its chart series in real-time.

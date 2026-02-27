## Why

The frontend design features an `AtmDecayOverlay` component that visualizes SPY 0DTE decaying percentages (Straddle, Call, Put) anchored to the 9:30 AM ET opening ATM strike price. Currently, this visual representation is handled entirely by a TradingView widget without any coordinated backend ingestion, anchoring, or persistence logic. 

To bridge this gap and provide a unified system state, the backend must capture the opening ATM prices, persist them, calculate the real-time decay (Theta/Vega drain), and broadcast the calculated percentages through the standard WebSocket pipeline. This is critical for data consistency, historical audits, and ensuring the interface functions correctly even if the external chart crashes or restarts.

## What Changes

1. **Opening Anchor Capture**: Implement logic to accurately identify the ATM strike at 9:30 AM ET and lock its Call, Put, and Straddle premiums.
2. **Persistence Layer**: Store this 9:30 AM anchor in Redis (using the existing `opening_atm_redis_ttl_seconds` configuration) and file storage to survive application restarts.
3. **Real-time Decay Calculation**: Compare incoming option chain data against the stored anchor to compute the dynamic `put_pct`, `call_pct`, and `straddle_pct`. 
4. **WebSocket Integration**: Update the `SnapshotBuilder` to inject these calculate values into the `ui_state.atm` object for frontend consumption.

## Capabilities

### New Capabilities
- `atm-decay-tracker`: Captures opening options premiums, calculates percentage changes dynamically, and manages persistence.

### Modified Capabilities
- `websocket-broadcaster`: Expand the update payload to securely stream the new ATM decay index data.

## Impact

- `app/services/system/snapshot_builder.py`
- `app/services/analysis/time_decay_factor.py` (or a dedicated new module)
- Redis data schemas
- Frontend `types/dashboard.ts` and `AtmDecayOverlay.tsx`

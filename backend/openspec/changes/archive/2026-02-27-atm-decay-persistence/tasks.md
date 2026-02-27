## 1. Backend Persistence Infrastructure

- [x] 1.1 Create `app/services/analysis/atm_decay_tracker.py` module
- [x] 1.2 Implement initialization logic that loads historical anchor data from Redis or fallback local JSON
- [x] 1.3 Implement Redis read/write saving function for anchor key `app:opening_atm:{YYYYMMDD}`
- [x] 1.4 Implement fallback local JSON write logic inside `backend/data/opening_atm` folder
- [x] 1.5 Implement Redis Time-Series list writer for `app:atm_decay_series:{YYYYMMDD}` to accumulate computed ticks

## 2. ATM Decay Calculation Logic

- [x] 2.1 Update the main application initialization to start the `AtmDecayTracker`
- [x] 2.2 Implement `AtmDecayTracker.update(chain, spot)` to identify target ATM strike at exactly 9:30 AM ET
- [x] 2.3 Once anchored, calculate real-time percentage metrics: `(current_price - anchor_price) / anchor_price` for Call, Put, and Straddle
- [x] 2.4 Append the resultant `ui_state.atm` tick object into the Time-Series list at a defined cadence
- [x] 2.5 Handle pre-market edge cases: skip calculations and return null configurations before 9:30 AM

## 3. Data Flow and API Updates

- [x] 3.1 Update `SnapshotBuilder.build()` to request and merge `AtmDecayTracker`'s latest metrics to `ui_state.atm`
- [x] 3.2 Verify that the `agent_g.data.ui_state` dictionary matches the new schema modifications for incremental WebSocket updates
- [x] 3.3 Create a new REST FastAPI route `GET /api/atm-decay/history` to serve the full array of historical points for the current day.

## 4. System Validation

- [x] 4.1 Launch Redis, Backend, and Frontend locally to verify continuous logging flow
- [x] 4.2 Monitor WebSocket payloads via browser DevTools to ensure `ui_state.atm.call_pct` (and siblings) are properly populated and updating in real-time

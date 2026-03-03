# Optimization Plan: Monitor Data Flow (Option-Style Alignment)

## Goal Description
Optimize the `ADBMsysteam_deploy/monitor` data flow by implementing **Cursor-Based Incremental Sync**.
Refines `DeltaDataManager` to maintain an in-memory buffer (`live_buffer`) and only fetch new records from Redis using a cursor (timestamp). This aligns with the `Option` project's architecture.

## User Review Required
> [!IMPORTANT]
> **Performance Note**: The current `processor.py` logic calls `preprocess_data` on the returned data. Since `DeltaDataManager` *also* preprocesses data internally to filter the delta, this results in **Double Processing**.
> - **Redundancy Fix**: We will modify `processor.py` to **SKIP** the redundant `preprocess_data` call when in `live` mode, as the buffer is already clean. This satisfies the "non-redundant" requirement.
>
> **Deployment Warning**: This plan assumes a **Single-Process** deployment (e.g., `gunicorn -w 1` or `python app.py`). In multi-worker setups, each worker maintains a separate data buffer, which is less efficient but functional.

## Proposed Changes

### Backend Optimization: Cursor-Based Incremental Fetch

#### [MODIFY] [delta_manager.py](file:///c:/Users/Lenovo/Desktop/Option/ADBMsysteam_deploy/monitor/data/storage/delta_manager.py)
**Reference**: `Option` uses `last_cursor` to fetch only new points.

- **Current State**: `get_live_data_delta` calls `_get_trading_day_window_data` -> reads full range `Open` to `Now`.
- **New State**:
    1.  **Data Structure**: Add `self.live_buffer` (DataFrame) and `self.cursor` (latest timestamp ms) to `DeltaDataManager`.
    2.  **Initialization**: On first load, fetch full `Open` to `Now`, populate buffer, set `cursor`.
    3.  **Incremental Sync**:
        - **Date Rollover / Reset**: Check if `self.cursor` belongs to a previous day. If so, clear buffer and force full reload.
        - **Fetch Delta**: Query Redis using `redis_reader.read_time_range(start=self.cursor, end=Now)`.
            - *Note*: Ensure query handles time overlap efficiently.
        - **Deduplication**: Drop rows from `new_data` where `timestamp <= self.cursor` to handle Redis inclusive range behavior.
        - **Update**: Append validated new rows to `self.live_buffer` and update `self.cursor`.
    4.  **Data Return**: Return `self.live_buffer` (full view) and `new_data` (incremental) to the application.

### Frontend Integration Analysis (Risk Assessment)

- **UI Components**: `monitor/ui/callbacks.py` expects a full DataFrame to render `go.Figure`.
    - **Outcome**: Our optimized backend returns the *Full* `live_buffer` every time.
    - **Impact**: The UI code requires **Zero Changes** and will function identically.
    - **Potential Issue**: Dash still serializes the full JSON dataset to the browser every 3-5 seconds.
    - **Mitigation**: This satisfies the "Backend Optimization" goal. Browser rendering optimization (extendData) is out of scope but can be added later without backend changes.

### Redundancy Cleanup [New]

#### [MODIFY] [processor.py](file:///c:/Users/Lenovo/Desktop/Option/ADBMsysteam_deploy/monitor/data/processors/processor.py)
- **Goal**: Prevent double-preprocessing.
- **Change**: In `process_data_pipeline`:
    - If `mode == 'live'`: The `df` returned from `get_live_data_delta` is already processed (from the buffer).
    - Skip the subsequent `df = self.preprocess_data(df)` line for this case.

## Verification Plan

### Manual Verification
1.  **Redis Monitor**: Use `redis-cli monitor` to observe commands.
    - **Before**: `ZRANGEBYSCORE timeline <Open> <Now>` (Range grows indefinitely).
    - **After**: `ZRANGEBYSCORE timeline <LastCursor> <Now>` (Range stays tiny, e.g., last 3 seconds).
2.  **Logs**:
    - Verify logs show "LiveDelta: Incremental sync, fetched N records" (where N is small, e.g., 1 or 0).
3.  **Correctness**:
    - Compare charts with the "Option" project (if running in parallel) or run side-by-side with unpatched version to ensure data matches exactly.

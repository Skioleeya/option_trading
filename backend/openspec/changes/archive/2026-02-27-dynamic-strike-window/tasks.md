# Tasks: Dynamic Strike Window Implementation

## 1. Backend Configuration & Research Logic

- [x] 1.1 Add `strike_window_size` (default 15.0) and `research_window_size` (default 70.0) to `app/config.py`
- [x] 1.2 Implement `OptionChainBuilder._fetch_volume_distribution()` to perform the wide-window scan

## 2. Implementation: Adaptive OptionChainBuilder

- [x] 2.1 Modify `OptionChainBuilder` to store an internal `volume_map`
- [x] 2.2 Implement logic to find the "Active High-Volume Cluster" around the spot price
- [x] 2.3 Refactor `_get_option_chain` to use the adaptive window or research-backed hot zone
- [x] 2.4 Ensure `fetch_chain` triggers research scans at the appropriate frequency

## 3. System Validation

- [x] 3.1 Verify "Volume Map" accuracy by comparing with full-chain data logs
- [x] 3.2 Confirm that the prioritized window correctly captures the 90th percentile of intraday volume
- [x] 3.3 Verify system stability when SPY makes a fast move (gap) and the window shifts/re-calculates

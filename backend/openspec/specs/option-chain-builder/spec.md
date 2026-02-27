# option-chain-builder Specification

## Purpose
TBD - created by archiving change dynamic-strike-window. Update Purpose after archive.
## Requirements
### Requirement: Volume Distribution Research
The `OptionChainBuilder` SHALL implement a "Research Scan" capability:
- **Scope**: Scan strikes within `+/- 70` points of current spot.
- **Output**: Build a map of Volume per Strike to identify liquidity clusters.
- **Interval**: Perform this scan on startup and periodically (e.g., every 30 minutes).

#### Scenario: Periodic scanning to identify liquidity walls
- **WHEN** the research interval has elapsed
- **THEN** it fetches symbols for the wide +/- 70 window
- **THEN** it fetches quotes in safe batches and updates the internal volume map

### Requirement: Adaptive Window Filtering
The `OptionChainBuilder` SHALL use the results of the Volume Distribution Research to determine the **Optimal Active Window**:
- **Constraint**: The final quote request SHALL NOT exceed API limits (if any) or excessive noise.
- **Default Baseline**: In the absence of research data, fallback to `+/- 15` points.

#### Scenario: Restricting quote requests to the active trading zone
- **WHEN** fetching the option chain
- **THEN** it filters contracts to only those within the `strike_window_size` of the current spot price
- **THEN** it executes the API requests in sub-batches to ensure stability

### Requirement: Spot-First Fetching
The `fetch_chain` method SHALL ensure that the underlying SPY spot price is retrieved and updated **before** any filtering or research logic.

#### Scenario: Sequence of price capture
- **WHEN** `fetch_chain` is called
- **THEN** it first requests the "SPY.US" price
- **THEN** it uses that price for filtering or research

### Requirement: Diagnostic Transparency
The `get_diagnostics` method SHALL report the number of contracts filtered vs. total available in the chain (if accessible) or at least the current active `chain_size`.

#### Scenario: Inspecting window state
- **WHEN** `get_diagnostics` is called
- **THEN** it returns the current `strike_window` size and `volume_map_size`

### Requirement: Long-Connection Initialization
The `OptionChainBuilder` SHALL configure the `QuoteContext` with a quote callback during initialization.

#### Scenario: Registering the push handler
- **WHEN** `initialize` is called
- **THEN** it creates the `QuoteContext`
- **THEN** it calls `ctx.set_on_quote(self._on_quote_callback)` to handle future pushes.

### Requirement: Push Data Integration
The `OptionChainBuilder` SHALL implement a callback method to process incoming real-time ticks and update the local state.

#### Scenario: Updating a contract when a tick is pushed
- **WHEN** the background SDK thread receives a `Quote` tick for a symbol
- **THEN** it updates the corresponding entry in the internal `_chain` dictionary
- **THEN** it updates fields like `last_done`, `ask`, `bid`, and `volume`.

### Requirement: Dynamic Subscription Lifecycle
The `OptionChainBuilder` SHALL manage the subscription list based on the active strike window (Spot ± 15).

#### Scenario: Syncing subscriptions as price moves
- **WHEN** `fetch_chain` is called
- **THEN** it identifies symbols for the current ±15 point window
- **THEN** it identifies "new" symbols (not yet subscribed) and calls `ctx.subscribe(new_symbols, [QuoteType.Quote], SubType.Quote)`
- **THEN** it identifies "stale" symbols (outside the window) and calls `ctx.unsubscribe(stale_symbols)`
- **THEN** it maintains a list of `self._subscribed_symbols` to prevent redundant API calls.

### Requirement: Non-Blocking State Access
The `fetch_chain` method SHALL return the in-memory state without performing blocking network requests for quotes.

#### Scenario: High-speed snapshot retrieval
- **WHEN** the main loop requests the current option chain
- **THEN** `OptionChainBuilder` returns the symbols and their last-pushed values from `self._chain` immediately.


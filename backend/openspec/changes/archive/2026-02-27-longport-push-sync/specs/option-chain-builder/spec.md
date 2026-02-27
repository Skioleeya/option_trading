# Specification: WebSocket Push Synchronization
# MODIFIED option-chain-builder

## ADDED Requirements

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

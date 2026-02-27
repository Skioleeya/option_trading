# Tasks: WebSocket Push Integration (Phase 33)

## 1. Prototype & Callback Setup
- [x] 1.1 Implement `_on_quote_callback` in `OptionChainBuilder` to handle incoming pushes
- [x] 1.2 Update `initialize` to register the callback with `QuoteContext.set_on_quote`
- [x] 1.3 Add `self._subscribed_symbols` (set) to track active subscriptions

## 2. Subscription Management Logic
- [x] 2.1 Refactor `fetch_chain` to perform differential subscription (Sync vs target ±15 window)
- [x] 2.2 Implement robust `unsubscribe` for symbols that fall out of the active window
- [x] 2.3 Implement a "Warm-up" fetch (REST) when a symbol is first subscribed to populate initial Bid/Ask

## 3. Execution & Memory Sync
- [x] 3.1 Update `_get_option_chain` to return the current `self._chain` dictionary values
- [x] 3.2 Ensure `self._chain` is correctly initialized with symbols before the first push arrives
- [x] 3.3 Add logging for subscription events (New/Removed) for debugging

## 4. Verification
- [x] 4.1 Verify that UI updates are triggered by WebSocket pushes rather than polling
- [x] 4.2 Check subscription count in `get_diagnostics` to ensure it stays near ~60 and never exceeds 100
- [x] 4.3 Test "Follow Spot" logic by observing subscriptions as SPY price moves significantly

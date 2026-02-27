# Proposal: WebSocket Push-based Option Chain Synchronization

## Why
Currently, the `OptionChainBuilder` polls the Longport API via `option_quote(symbols)` in every processing loop. This approach has several drawbacks:
1.  **Latency**: Data is only as fresh as the polling interval (1-3 seconds).
2.  **API Thrashing**: Repeated requests for the same set of contracts even when no price changes occurred.
3.  **Stability**: High polling frequency can trigger "Excessive Requests" or rate limits during high volatility.

## What
Switch to a **Push-based** model using Longport SDK's native WebSocket (`subscribe`) capability.

## Capabilities
- **Real-time Callbacks**: Implement an `on_quote` handler to update the internal `OptionChainBuilder` state immediately as ticks arrive.
- **Dynamic Subscription Management**: Automatically `subscribe` to symbols entering our ±15 strike window and `unsubscribe` from symbols that drift out.
- **Memory Consistency**: `fetch_chain` will now return the latest state cached in memory, ensuring zero network latency for the main runner loop.
- **Resource Efficiency**: Drastically reduces REST API calls, respecting the 100-symbol subscription limit per context.

## Impact
- **Sub-second Refresh**: UI updates will reflect market moves within milliseconds of the provider push.
- **Improved Calculation Accuracy**: Greeks and GEX will be computed on truly real-time data.
- **Enhanced Reliability**: Leverages standard long-connection patterns documented by Longport.

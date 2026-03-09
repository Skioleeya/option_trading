## Why

L0 Python components currently depend on concrete `QuoteContext` ownership, which keeps Python tied to connection lifecycle details and blocks rust-only migration.

## What Changes

Introduce and adopt a runtime protocol (`L0QuoteRuntime`) across L0 orchestrators:

- `OptionSubscriptionManager`
- `FeedOrchestrator`
- `IVBaselineSync`
- `Tier2Poller`
- `Tier3Poller`
- `OptionChainBuilder`

## Outcome

Python modules become transport-agnostic and consume only runtime capabilities, not SDK ownership internals.


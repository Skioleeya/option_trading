## Context

`QuoteContext` references leak into scheduler, poller, and builder code. This proposal replaces direct SDK dependency with protocol-based runtime abstraction.

## Decisions

1. Define `L0QuoteRuntime` protocol as the only quote access contract in L0 Python orchestration.
2. Provide two implementations:
   - `RustQuoteRuntime` (default)
   - `PythonQuoteRuntime` (fallback only)
3. Route all blocking quote pulls through async wrappers to protect event-loop latency.

## Constraints

- Keep L0-L4 payload fields unchanged.
- Keep strict layer boundaries; no new cross-layer imports.


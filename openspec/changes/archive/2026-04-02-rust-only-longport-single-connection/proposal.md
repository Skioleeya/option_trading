## Why

The current dual-stack topology (`Python QuoteContext` + `RustIngestGateway`) can violate the broker-side "single long-lived connection per account" policy and introduces non-deterministic reconnect behavior during high-volatility windows.

## What Changes

This parent proposal defines the governance boundary for a staged migration to `rust_only` runtime:

1. Keep migration split into three executable child proposals.
2. Require child dependency order: `A -> B -> C`.
3. Set one acceptance gate for closure: all children completed and strict session validation passed.

## Scope

- Architecture orchestration, dependency ordering, rollback policy, and acceptance gates.
- No direct runtime code implementation in this parent proposal.

## Child Proposals

- `rust-ffi-quote-rest-runtime`
- `python-quotecontext-decouple`
- `rust-only-cutover-cleanup`

## Rollback

If any child proposal fails hard runtime regression, the rollout halts and reverts to the latest validated checkpoint before the failing child.


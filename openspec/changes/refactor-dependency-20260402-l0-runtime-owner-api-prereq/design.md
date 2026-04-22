## Context

Current L0 runtime Rust migration already exposes many helper functions via
`shared.services.l0_runtime._native_generated.l0_rust`, but core runtime/service owner classes are
still Python-owned. Downstream cutover proposal `impl-20260402-l0-runtime-rust-cutover` cannot
close sub-waves E/F safely without explicit owner-API replacement contracts.

## Goals / Non-Goals

**Goals:**
- define the minimum Rust owner-API surface required before Python owner retirement
- define consumer retarget sequence and parity evidence requirements
- define strict blocking criteria for Sub-wave E/F and dual-run closure

**Non-Goals:**
- no runtime code implementation in this child
- no direct deletion of Python owner files
- no LongPort gateway behavior changes

## Decisions

1. Use a dedicated dependency child instead of mixing prerequisite definition into impl wave.
   - Rationale: prevents scope diffusion and keeps impl cutover DoD auditable.
2. Freeze owner-API prerequisite list as a governed contract:
   - `OptionChainBuilder`
   - `L0QuoteRuntime` / `RustQuoteRuntime`
   - `APIRateLimiter`
   - `FeedOrchestrator`
   - `OptionSubscriptionManager`
   - `IVBaselineSync`
   - `build_runtime_bundle`
   - `CallbackHooks` / `SnapshotRequest`
3. Require retarget-before-delete sequence:
   - owner API exists -> consumers retarget -> parity tests pass -> Python owner deletion.
4. Keep Sub-wave F dual-run requirement explicit and non-waivable in this chain.

## Risks / Trade-offs

- [Risk] prerequisite list incomplete -> [Mitigation] keep list contractual in spec and tasks; block closure when any item missing.
- [Risk] downstream impl proceeds with helper-only exports -> [Mitigation] make this child a formal blocker in impl proposal `BLOCKED_BY`.
- [Risk] ambiguous ownership between `shared_rust` and `_native_generated.l0_rust` -> [Mitigation] require owner mapping evidence in downstream handoff.

## Migration Plan

1. Create and validate this dependency child (`proposal/design/spec/tasks`).
2. Rewire impl proposal blocker to this child.
3. Downstream session implements owner APIs and records parity evidence.
4. After owner APIs are landed and verified, continue Sub-wave A-G deletions.

## Open Questions

- Which owner APIs should live in `shared_rust.*` versus `l0_rust` extension namespace?
- Should `CallbackHooks`/`SnapshotRequest` migrate to `shared_rust.contracts` or remain layer-local contracts?

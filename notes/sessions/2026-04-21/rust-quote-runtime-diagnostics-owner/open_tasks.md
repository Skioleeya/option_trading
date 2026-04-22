# Open Tasks

## Priority Queue
- [x] P0: Move `RustQuoteRuntime.diagnostics()` off the live gateway and onto a borrow-free diagnostics owner surface.
  - Owner: Codex
  - Definition of Done: diagnostics no longer calls the live gateway object directly, tests pass, and a fresh real-host window keeps borrow/rest/shutdown counts at zero.
  - Blocking: none.
- [ ] P1: Decide whether more gateway internals beyond `spy_push_diag` need to be promoted into the independent diagnostics handle.
  - Owner: Codex
  - Definition of Done: either explicitly keep the current push-only scope or extend the native handle surface in a follow-up session.
  - Blocking: none.
- [ ] P2: Add one higher-level diagnostics freshness regression if operations later require proving snapshot lag bounds under sustained load.
  - Owner: Codex
  - Definition of Done: test/harness exists with a defined freshness SLA.
  - Blocking: currently no explicit freshness SLA exists.

## Parking Lot
- [ ] Evaluate whether builder/runtime status paths should cache one merged diagnostics object per tick instead of invoking `quote_runtime.diagnostics()` multiple times in the same request/build cycle.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Replaced live-gateway diagnostics reads with an independent diagnostics handle and cached snapshot in `RustQuoteRuntime` (2026-04-21 18:37 ET).

# Open Tasks

## Priority Queue
- [x] P0: Hard-cut the `RustQuoteRuntime` REST-path `Already borrowed` warnings caused by concurrent gateway access.
  - Owner: Codex
  - Definition of Done: single gateway owner is serialized, targeted concurrency regression passes, and a fresh real-host restart window shows zero new borrow warnings.
  - Blocking: none.
- [ ] P1: Decide whether `RustQuoteRuntime.diagnostics()` should also stop touching the live PyO3 gateway directly and instead rely on a cached snapshot surface.
  - Owner: Codex
  - Definition of Done: either prove the current `&self` diagnostics path is safe enough, or move it behind the same owner contract in a follow-up session.
  - Blocking: none.
- [ ] P2: Add a higher-level regression that exercises concurrent `IVBaselineSync` / `FeedOrchestrator` calls against the same runtime owner once a clean deterministic harness exists.
  - Owner: Codex
  - Definition of Done: one test proves the owner contract under realistic concurrent call sites, not just a unit serializer.
  - Blocking: harness complexity.

## Parking Lot
- [ ] Evaluate whether a dedicated single-thread executor would be preferable to the current thread-lock serializer if native gateway call duration grows materially.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Serialized all native `RustIngestGateway` calls in `RustQuoteRuntime` and cleared fresh real-host `Already borrowed` warnings in the new log window (2026-04-21 18:21 ET).

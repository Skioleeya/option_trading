# Open Tasks

## Priority Queue
- [x] P0: Hard-cut the `ArrowIpcReader.close(): Already borrowed` shutdown-path failure.
  - Owner: Codex
  - Definition of Done: native close no longer requires mutable PyO3 borrow, blocked reads are interruptible, and repeated real-host restarts stay green.
  - Blocking: none.
- [ ] P1: Investigate the unrelated runtime warnings where quote REST operations can still surface `Already borrowed` inside `RustQuoteRuntime` request paths.
  - Owner: Codex
  - Definition of Done: prove whether those warnings are a distinct gateway borrow owner or clear them if they are already obsolete.
  - Blocking: none.
- [ ] P2: Add an environment-supported native regression for `NativeArrowIpcReader` close/read concurrency once the crate can run PyO3-linked tests in CI without the current linker limitation.
  - Owner: Codex
  - Definition of Done: automated close/read race regression runs in the normal Rust test entry.
  - Blocking: current local `cargo test` lib-test link limitation.

## Parking Lot
- [ ] Evaluate whether `ArrowIpcReader` should expose an explicit async `close_and_wait()` surface if future shutdown owners need deterministic thread-join semantics.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Replaced mutable-borrow native close with interruptible immutable close on `NativeArrowIpcReader` and validated repeated real-host restart health (2026-04-21 18:11 ET).

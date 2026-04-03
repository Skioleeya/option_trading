## Context

`wall_context_builder.py` sits in the L1 microstructure path and still owns NumPy-backed math.
The cleanup list correctly points out that the existing Rust module `microstructure.rs` is the
natural home for the missing numerical helper instead of another new module.

## Goal

Complete the wall-context numerical cutover with the smallest viable migration surface:

- extend existing `microstructure.rs`
- keep Python as orchestration only
- avoid wrapper proliferation

## Non-Goals

- No contract redesign for L1 microstructure payloads
- No new `shared/services/*` compatibility wrapper
- No unrelated tracker or presenter changes

## Proposed Rust Ownership

The Rust side should own the numerical reductions or scoring used to build wall context. Python
should keep only:

- orchestration and result mapping
- invocation of the Rust helper
- non-hot-path shape adaptation for list-of-dicts input

For the `pa.RecordBatch` case, the Rust surface must preserve the Arrow-first hot path. That
means the cutover must not materialize Python lists, `to_numpy()` arrays, or other copied
intermediates before entering Rust on the live `RecordBatch` branch.

Acceptable directions include:

- Arrow / C data interface handoff into Rust
- a Rust helper that consumes Arrow buffers or arrays directly

Unacceptable direction:

- Python-side extraction of `strike` / `volume` into copied sequences on the `RecordBatch` path

## File-Length Guard

If extending `microstructure.rs` would break the 400-line limit, split by responsibility inside
the same Rust ownership cluster rather than creating a Python bridge file.

## Cross-Proposal Dependency

This cutover should reuse the marshalling precedent established by the two bridge-audit
proposals, so the Python wrapper stays minimal and consistent.

## Success Signal

Both input shapes remain correct after cutover:

- `list[dict]` path preserves existing semantics
- `RecordBatch` path preserves Arrow-first hot-path behavior without added Python copies

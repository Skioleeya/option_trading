## Context

`streaming_aggregator.py` is only partially Rust-owned. The bridge question is real, but the
file also still owns cumulative flip calculation in Python and rebuilds NumPy arrays inside
`_recompute_walls()`. That means bridge cleanup cannot be treated as a self-sufficient endpoint.

## Goal

Turn the current ambiguity into an explicit repository rule while preventing a false-close of the
cleanup item:

- preferred path: native Python sequences into Rust
- fallback path: NumPy retained only as documented bridge marshalling
- residual Python wall / flip compute must be retired or explicitly chained forward
- `flip_level_cumulative` must be returned by the Rust aggregate payload, not interpolated in Python

## Non-Goals

- No unrelated L2/L3/L4 changes
- No pretending that bridge cleanup alone resolves the file

## Decision Frame

1. Inspect the currently imported Rust functions used by `streaming_aggregator.py`.
2. Run a small direct-call proof to verify whether Python lists are accepted.
3. Inventory the residual Python numerical work in `_recompute_walls()` / `_find_flip_level()`.
4. Choose one of two acceptable closure shapes:
   - Outcome A: remove `numpy` import and `np.asarray(...)`
   - Outcome B: keep minimal marshalling and annotate it as bridge-only retention
5. In both outcomes, the proposal must either:
   - retire the residual Python wall / flip owner in the same wave, or
   - stay open and reference the concrete successor proposal that will do so

## Engineering Constraints

- The file must remain Rust-only for compute.
- The audit must not create a new wrapper file.
- Any retained `numpy` line must be visibly non-compute and easy to grep.
- `_find_flip_level()` cannot be silently left behind as “acceptable residual Python math”.

## Success Signal

Future Rust cutover proposals can reference this change as the PyO3 marshalling precedent for
`shared_rust.services` sequence handling, without misreading it as permission to leave residual
Python runtime compute behind.

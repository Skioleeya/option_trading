## Context

`greeks_engine.py` sits on the boundary between L1 orchestration and lower-level compute
owners. The live path currently builds arrays for `bsm_fast.compute_greeks_batch()`, which is a
Python runtime compute owner rather than a thin FFI bridge. That means this proposal cannot
close as “bridge cleanup” unless the downstream owner is proven to be a valid final exception or
is explicitly chained to a real migration.

## Goal

Produce a precise classification for each surviving NumPy allocation in `greeks_engine.py`:

- removable bridge noise
- required owner-interface allocation to a valid final owner
- blocked-on-migration allocation feeding a Python runtime compute owner

## Non-Goals

- No new compute owner
- No change to Greeks semantics
- No broad reactor or GPU-kernel refactor

## Decision Rules

1. If a downstream owner accepts Python sequences directly, use them and remove NumPy.
2. If a downstream owner requires a dense array type, retain the allocation with an explicit
   owner-boundary explanation.
3. If a downstream owner is `bsm_fast` or another Python runtime compute owner, this proposal
   must not claim cleanup completion; it must link the real owner migration.
4. If a call site mixes concerns, split the explanation by owner rather than keeping a vague
   file-level justification.

## Cross-Proposal Value

This proposal complements the `streaming_aggregator` change. Together they define the
batch-input precedent for the upcoming `attention_fusion` and `wall_context_builder` cutovers
without allowing “audit-only” closure over live Python compute owners.

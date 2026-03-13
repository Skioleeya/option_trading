# Open Tasks

## Priority Queue
- [x] P0: Integrate official LongPort `premium/standard` diagnostics into research metadata
  - Owner: Codex
  - Definition of Done:
    - Tier2/Tier3 caches retain `premium` and `standard`.
    - `compute_loop` passes summarized diagnostics via L1 extra metadata.
    - research feature store exposes explicit LongPort diagnostics columns.
  - Blocking: None
- [x] P1: Decide official `historical_volatility_decimal` adoption path
  - Owner: Codex
  - Definition of Done:
    - Choose whether `option_quote()`-sourced historical HV should augment or replace local rolling RV in research/runtime.
    - Document quota/contract implications before implementation.
  - Blocking: None
  - SUPERSEDED-BY: 2026-03-12/historical-vol-decimal-research-only-impl
- [ ] P2: Add direct Tier2/Tier3 poller regression coverage for `premium/standard`
  - Owner: Codex
  - Definition of Done:
    - Dedicated unit tests verify metadata refresh and cache rows keep `standard`.
    - Dedicated unit tests verify `calc_indexes(...Premium)` cache rows keep `premium`.
  - Blocking: Requires poller test harness setup.

## Parking Lot
- [ ] Consider surfacing LongPort diagnostics on a debug endpoint if operators want live monitoring.
- [ ] Consider consolidating LongPort diagnostics naming under one neutral shared schema if more fields are adopted.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Official LongPort `premium/standard` research diagnostics follow-up completed (2026-03-12 15:13 ET)



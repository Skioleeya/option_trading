## Why

Current live diagnostics show a sustained feature-collapse pattern in the L0/L1/L2 chain:

1. `vpin_composite` and `bbo_imbalance_ewma` stay near zero because Rust SHM events do not fully drive the L1 microstructure callback path.
2. `peak_impact`/`max_impact` can degrade to zero on the `RecordBatch` path because extractor logic assumes dict-style rows and legacy gamma keying.
3. `turnover_velocity` can remain zero for long windows when WS turnover is absent, despite REST contracts preserving turnover-related fields.

This is a runtime behavior integrity issue, not a UI-only issue.

## What Changes

1. Complete Rust SHM -> L1 microstructure bridge so depth/trade events can drive `on_depth`/`on_trade` update paths without breaking L0->L1->L2 direction.
2. Update L2 impact extraction contract to support `RecordBatch` inputs and `computed_gamma` compatibility while preserving legacy dict compatibility.
3. Add controlled turnover fallback under a WS-authoritative policy:
   - WS turnover remains primary.
   - REST turnover/current_volume may be used only as bounded fallback when WS-side turnover is unavailable.
   - Field semantics follow `docs/LONGPORT_OPTION_FIELD_DICTIONARY.md`.

## Impact

- Restores microstructure feature continuity and prevents systematic all-zero telemetry drift.
- Keeps failure handling explicit and observable (no silent drop behavior).
- Preserves existing architecture boundaries and runtime ownership model.

## Out of Scope

- No L4 presentation redesign.
- No broad contract rename or schema migration outside the targeted feature path.
- No refactor-governance parent/child proposal split in this change.


## Final shared_rust.* Surface — Canonical Layout (2026-04-02)

### Four-Pyd Decision

| Module | Compiled File | Source Crate | Consumer Layers | Size |
|---|---|---|---|---|
| `shared_rust.services` | `shared_rust/services.pyd` | `shared_rust_services/` | L1, L2, L3, app | 2.7 MB |
| `shared_rust.services_l0_support` | `shared_rust/services_l0_support.pyd` | `shared_rust_l0_support/` | L0 only | 912 KB |
| `shared_rust.contracts` | `shared_rust/contracts.pyd` | (compiled artifact) | app, L0 | 347 KB |
| `shared_rust.models` | `shared_rust/models.pyd` | (compiled artifact) | L1, L2 | 602 KB |

**Why keep four separate pdys (not merge):**
- `services_l0_support` is L0-only; adding to `services` would create L0→L1 namespace
  pollution and violate layer boundary law.
- `contracts` and `models` are data-contract crates versioned independently from
  analytical compute services.
- No consumer confusion: each import path is unique and stable across all sessions since
  Wave 16.

### Registered Modules in shared_rust.services (lib.rs, 2026-04-02)

```
mod header_context;         // HeaderVolatilityContextService
mod history;                // build_columnar_payload, HistoryWindow
mod realized;               // RollingRealizedVolatility
mod research_schema;        // ResearchSchema types
mod research_store;         // ResearchFeatureStore
mod research_store_support; // internal helper (not directly registered)
mod research_utils;         // research utility functions
mod active_options;         // ActiveOptionsEngine (Wave 18)
mod tactical;               // DEGComposer, FlowEngineD/E/G, tactical_compute_vrp
mod bsm;                    // bsm_batch_numpy_tier, norm_cdf
mod aggregation;            // aggregate_greeks_full, select_walls
mod aggregation_rust_bridge;// aggregate_from_greeks, estimate_zero_gamma_level (internal)
mod microstructure;         // compute_vpin_regime, compute_vol_accel_entropy, compute_entropy_gate
mod sabr;                   // calibrate_sabr, sabr_iv
```

**Note:** `research_store_support` and `aggregation_rust_bridge` are internal helper modules
used by sibling modules; they are NOT directly registered as Python-callable. This is
intentional — they are implementation details, not public API.

### Non-Canonical Import Patterns to Scan

| Pattern | Expected Result | Action if Found |
|---|---|---|
| `shared_rust.services_root` | 0 matches (pyd deleted) | Re-verify deletion + retarget |
| `shared_rust.services_tmp` | 0 matches | Retarget to `shared_rust.services` |
| `import shared_rust_services` | 0 matches (wrong layer) | Retarget to `shared_rust.services` |
| `from shared_rust import services_root` | 0 matches | Same |
| `from shared_rust import services_l0_support` | allowed (L0 only) | No action |

### Canonical Import Verification (Spot Check)

Key consumers already confirmed on `shared_rust.services`:
- `l1_compute/aggregation/rust_bridge.py` — `aggregate_greeks_full`, `select_walls`, etc.
- `l1_compute/analysis/bsm_rust_bridge.py` — `bsm_batch_numpy_tier`
- `l2_decision/signals/flow/deg_composer.py` — `DEGComposer`
- `l2_decision/signals/flow/flow_engine_d.py` — `FlowEngineD`
- `l3_assembly/assembly/ui_state_tracker.py` — (via tactical module)
- `app/loops/compute_loop.py` — (multiple imports)

PARENT_CHANGE_ID: refactor-governance-20260401-rust-runtime-migration-chain
DEPENDENCY_ORDER: 23
BLOCKED_BY: refactor-dependency-20260402-services-root-retirement (DONE 2026-04-02)

## Why

The global backlog item "Collapse temporary Rust-only service module names into the final
`shared_rust.services` namespace" was registered after Wave 16 when `services_root.pyd` was
still live. As of 2026-04-02:

- `services_root.pyd` deleted (refactor-dependency-20260402-services-root-retirement, DONE)
- All 12 analytical modules registered in `shared_rust_services/src/lib.rs` and exported
  via `shared_rust.services` (bsm, aggregation, microstructure, sabr, active_options,
  header_context, history, realized, research_store, tactical — L1-Wave implementations)
- No temporary module names or alternate pyd paths found in any runtime consumer

This proposal closes the backlog item with a verification scan and records the final
four-pyd surface decision so future sessions do not re-open the question.

## What Changes

1. **Verification scan** — confirm zero consumers of non-canonical `shared_rust.*` paths.
2. **Surface decision record** — document that the four-pyd layout is intentional and final:
   - `shared_rust.services` — all analytical services (L0–L3 compute owners)
   - `shared_rust.services_l0_support` — L0-specific native bridge (MVCCChainStateStore, l0_*)
   - `shared_rust.contracts` — data contracts (CallbackHooks, SnapshotRequest)
   - `shared_rust.models` — L1/L2 data models (VannaFlowResult, IVVelocityResult)
3. **Backlog closure** — mark `notes/context/open_tasks.md` item as [x].

## Scope

In:
- `notes/context/open_tasks.md` — close backlog item
- `docs/SOP/SYSTEM_OVERVIEW.md` — add Rust surface section (or SOP-EXEMPT with reason)

Out:
- `shared_rust_services/src/lib.rs` — no Rust source changes
- `shared_rust/*.pyd` — no pyd changes; no merging of pyd files
- Any runtime Python consumer file — no changes unless non-canonical import found

## Hard Governance Prohibitions

- Must not merge `contracts.pyd` or `models.pyd` into `services.pyd`.
- Must not add compatibility shims for `services_root` or any retired path.
- Must not modify `shared_rust_services/src/lib.rs` for namespace reasons alone.
- If no non-canonical imports are found, this is verification-only; zero code changes.

## Verification Gate

1. `rg "shared_rust\.(services_root|services_tmp)" --glob "*.py" app l0_ingest l1_compute l2_decision l3_assembly l4_ui shared` → 0 matches
2. `rg "import shared_rust_services" --glob "*.py" app l0_ingest l1_compute l2_decision l3_assembly l4_ui shared` → 0 matches
3. `python -c "from shared_rust.services import bsm_batch_numpy_tier, aggregate_greeks_full, compute_vpin_regime, calibrate_sabr; print('ns-ok')"` → prints `ns-ok`
4. `pwsh scripts/validate_session.ps1 -Strict` → PASS

## Rollback

No runtime code is changed. If SOP update is reverted: `git restore docs/SOP/SYSTEM_OVERVIEW.md`.

## Risk

LOW. Verification-only unless a stray non-canonical import is found. If found, retargeting
is a one-line change per site with zero behavior impact.

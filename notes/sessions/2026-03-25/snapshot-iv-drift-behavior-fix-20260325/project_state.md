# Project State

## Snapshot
- DateTime (ET): 2026-03-25 09:37:01 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `70cc81b`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Apply the minimal behavior fix for `snapshot_version_iv_probe` so slow-cadence `rest` ATM IV does not trigger false drift while also reducing `app/loops/compute_loop.py` back under the 400-line policy ceiling.
- Scope In: app-loop helper/probe split, cadence-aware probe suppression and context reset logic, targeted pytest coverage, live backend restart, SOP updates, and session/context records.
- Scope Out: Any L1 IV resolver redesign, non-`rest` source suppression expansion, or cross-layer contract/schema changes.

## What Changed (Latest Session)
- Files: Added `app/loops/compute_metadata.py` and `app/loops/compute_probe.py`; refactored `app/loops/compute_loop.py`; updated `app/loops/tests/test_compute_loop_helpers.py`, `app/tests/test_compute_loop_timestamp.py`, `docs/SOP/L1_LOCAL_COMPUTATION.md`, and `docs/SOP/SYSTEM_OVERVIEW.md`.
- Behavior: `snapshot_version_iv_probe` now suppresses drift accumulation when `atm_iv_context.iv_source=rest`, resets when `atm_symbol` or `iv_source` changes, and publishes `last_atm_symbol/last_iv_source/suppressed_reason` in diagnostics. `compute_loop.py` is reduced to 329 lines.
- Verification: Targeted pytest passed. Backend was restarted live and `/debug/persistence_status` now shows `drift_active=false`, `mismatch_count=0`, and `suppressed_reason=non_reactive_iv_source:rest` / `atm_symbol_changed:...` while versions continue advancing.

## Risks / Constraints
- Risk 1: Only `rest` is currently classified as non-reactive; if `chain` or `sabr` later exhibit the same cadence mismatch, they will need a follow-up semantics review backed by live evidence.
- Risk 2: Startup warm-up still emits transient placeholder/ATM-decay diagnostics before the live chain fully populates; those warnings were observed during restart and are pre-existing behavior, not caused by this fix.

## Next Action
- Immediate Next Step: Run strict session validation, then keep a small follow-up task open to observe the probe on a genuinely fast-cadence `ws` ATM IV path.
- Owner: `Codex`

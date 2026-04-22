# Project State

## Snapshot
- DateTime (ET): 2026-04-02 06:47:51 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `7fb0f53`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: move `active_options` consumer imports off package-internal paths before deleting the package owner tree
- Scope In:
  - `shared/services/active_options_*` root-neutral import surfaces
  - `app/container.py`
  - `app/loops/compute_loop.py`
  - `app/loops/housekeeping_loop.py`
  - `l2_decision/signals/flow/*`
  - `l3_assembly/presenters/ui/active_options/presenter.py`
- Scope Out:
  - Rust owner replacement for `ActiveOptionsRuntimeService`
  - deletion of `shared/services/active_options/*`
  - `l0_runtime` migration wave

## What Changed (Latest Session)
- Files:
  - updated `AGENTS.md`
  - added `shared/services/active_options_constants.py`
  - added `shared/services/active_options_engines.py`
  - added `shared/services/active_options_input.py`
  - added `shared/services/active_options_runtime.py`
  - updated `app/container.py`
  - updated `app/loops/compute_loop.py`
  - updated `app/loops/housekeeping_loop.py`
  - updated `l2_decision/signals/flow/__init__.py`
  - updated `l2_decision/signals/flow/deg_composer.py`
  - updated `l2_decision/signals/flow/flow_engine_d.py`
  - updated `l2_decision/signals/flow/flow_engine_e.py`
  - updated `l2_decision/signals/flow/flow_engine_g.py`
  - updated `l3_assembly/presenters/ui/active_options/presenter.py`
- Behavior:
  - app/l2/l3 consumers now resolve ActiveOptions through root-neutral `shared.services` surfaces instead of package-internal submodules
  - `shared/services/active_options/*` remains the concrete owner for now, but package internals are no longer imported directly by runtime consumers in this slice
  - `AGENTS.md` now hard-requires minimum-file migration strategy and forbids wrapper fan-out when an existing neutral surface can absorb the cutover
- Verification:
  - `app/tests/test_lifespan_startup.py` passed
  - `app/loops/tests/test_compute_loop_helpers.py` passed
  - `app/loops/tests/test_housekeeping_gpu_dedup.py` passed
  - import smoke passed for `l2_decision.signals.flow` and `l3_assembly.presenters.ui.active_options.presenter`
  - `python scripts/policy/check_openspec_chain.py --repo-root . --meta-file notes/sessions/2026-04-02/wave18-active-options-rust-cutover/meta.yaml --handoff-file notes/sessions/2026-04-02/wave18-active-options-rust-cutover/handoff.md` passed
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passed

## Risks / Constraints
- Risk 1: this session establishes a transitional import layer; the underlying `shared/services/active_options/*` package still exists and must be retired in a follow-up slice
- Risk 2: Rust owner cutover for ActiveOptions remains open, so this session should be treated as Wave 18 entry tranche rather than final owner replacement

## Next Action
- Immediate Next Step: finish Wave 18 by reusing the existing root-neutral entrypoints, replacing owners behind them, and deleting `shared/services/active_options/*` without adding another wrapper layer
- Owner: Codex

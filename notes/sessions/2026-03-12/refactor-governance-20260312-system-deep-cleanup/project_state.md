# Project State

## Snapshot
- DateTime (ET): 2026-03-12 23:34:09 -04:00
- Branch: `master`
- Last Commit: `8ad09df`
- Environment:
  - Market: `UNVERIFIED`
  - Data Feed: `UNVERIFIED`
  - L0-L4 Pipeline: `UNVERIFIED`

## Current Focus
- Primary Goal: Execute parent+child OpenSpec governance and implement scoped deep-cleanup refactor on app loop hot paths with strict boundary discipline.
- Scope In:
  - Build parent proposal + 4 child proposals (`dependency -> nesting -> bloat -> magic-number`) with required metadata and task templates.
  - Eliminate app-loop private cross-layer access (`ctr.option_chain_builder._iv_sync`) via public API boundary.
  - Reduce hot-path complexity/nesting/LOC and remove business magic numbers in `run_compute_loop` and `run_housekeeping_loop`.
  - Verify with pytest wrapper + layer boundary scan + quantitative before/after metrics.
- Scope Out:
  - Full-repo complexity normalization (e.g., `l2_decision/agents/agent_g.py`) is not included in this scoped execution.
  - No contract schema changes (`CleanQuoteEvent`, `EnrichedSnapshot`) and no SHM layout changes.

## What Changed (Latest Session)
- Files:
  - `l0_ingest/feeds/option_chain_builder.py`
  - `app/loops/compute_loop.py`
  - `app/loops/housekeeping_loop.py`
  - `app/loops/tests/test_compute_loop_helpers.py`
  - `app/loops/tests/test_compute_loop_gpu_dedup.py`
  - `openspec/changes/refactor-governance-20260312-system-deep-cleanup/*`
  - `openspec/changes/refactor-dependency-20260312-layer-decouple/*`
  - `openspec/changes/refactor-nesting-20260312-core-loops/*`
  - `openspec/changes/refactor-bloat-20260312-service-split/*`
  - `openspec/changes/refactor-magic-number-20260312-constants-governance/*`
- Behavior:
  - `OptionChainBuilder` exposes `get_iv_sync_context()` public API for app-loop orchestration.
  - `run_compute_loop` and `run_housekeeping_loop` are decomposed into smaller helpers, reducing branch complexity and nesting while keeping runtime behavior unchanged.
  - Magic numbers in the two hot loops are replaced with named constants.
  - OpenSpec parent+child chain is fully materialized; child proposals marked complete.
- Verification:
  - `scripts/test/run_pytest.ps1 app/loops/tests/test_compute_loop_helpers.py app/loops/tests/test_compute_loop_gpu_dedup.py app/loops/tests/test_housekeeping_gpu_dedup.py`
  - `scripts/policy/check_layer_boundaries.ps1`
  - quantitative before/after metric script (AST based)

## Risks / Constraints
- Risk 1: Repository still contains out-of-scope high-complexity modules (e.g., AgentG, trap detector) not addressed by this scoped pass.
- Risk 2: Global institutional thresholds are not yet guaranteed repository-wide; current evidence is scoped to target hot paths and related boundary change.

## Next Action
- Immediate Next Step: prepare next-session scope for L2 high-complexity modules (AgentG/TrapDetector) under new OpenSpec child chain.
- Owner: Codex



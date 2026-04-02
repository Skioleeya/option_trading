# Open Tasks

## Priority Queue
- [x] P0: Repair Active Options sparse-window fallback so live Top5 rows prefer real sub-threshold volume candidates before synthetic turnover/OI fillers.
  - Owner: Codex
  - Definition of Done: live sparse window shows `rows_real_non_synthetic=5`, `rows_synthetic_fallback=0`, `live_rows=5`, and payload rows are version-aligned through `/debug/active_options_capture`.
  - Blocking: none
- [x] P1: Add focused regression coverage for sparse fallback ordering and row-quality semantics.
  - Owner: Codex
  - Definition of Done: targeted pytest covers empty-filter and partial sparse fallback paths.
  - Blocking: none
- [x] P1: Sync SOP documentation for Active Options sparse fallback ordering.
  - Owner: Codex
  - Definition of Done: relevant SOP explicitly states sub-threshold real-volume preference ahead of synthetic fallback.
  - Blocking: none

## Parking Lot
- [ ] If strict host startup probe keeps flapping, stabilize quote startup connectivity on the strict path so future live verifications do not require degraded retry.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added sparse-fallback regression coverage in `shared/services/active_options/test_runtime_service_sparse_fallback.py`. (2026-04-01 09:41 ET)
- [x] Restarted the real host backend, followed strict-to-degraded boot policy, and verified live Active Options recovery with `verify_active_options_hotfix.ps1`. (2026-04-01 09:49 ET)

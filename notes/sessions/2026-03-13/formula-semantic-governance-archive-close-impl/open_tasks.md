# Open Tasks

## Priority Queue
- [ ] P1: Configure GitHub branch protection required check `validate-session`.
  - Owner: Repo Admin
  - Definition of Done: branch rule requires PR merge with passing `validate-session` check.
  - Blocking: repository admin access.
- [ ] P2: Calibrate `wall_collapse_flow_intensity_threshold` with historical/live samples.
  - Owner: Codex / next implementing agent
  - Definition of Done: threshold calibrated, validated, and documented in a dedicated implementation session.
  - Blocking: dedicated calibration data collection session.

## Parking Lot
- [ ] Decide if remaining old `Phase C` should stay intentionally open or be migrated into a fresh governed change after future scope review.
- [ ] Consider adding OpenSpec CI lint for stale `✓ Complete` changes older than N days without archive.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Archived follow-up phases `E/F/G/H` and parent `formula-semantic-followup-parent-governance` (2026-03-13 10:53 ET)
- [x] Archived old parent `formula-semantic-contract-parent-governance` and historical completed `A/B/D` (2026-03-13 10:53 ET)
- [x] Confirmed `openspec list` now keeps formula-semantic residual only at old `Phase C (0/10)` (2026-03-13 10:54 ET)
- [x] Passed strict session gate: `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` (2026-03-13 10:54 ET)

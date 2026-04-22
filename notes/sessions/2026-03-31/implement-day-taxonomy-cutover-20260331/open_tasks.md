# Open Tasks

## Priority Queue
- [x] P0: Implement canonical day taxonomy cutover in EOD archive code and tests.
  - Owner: Codex
  - Definition of Done: classifier emits canonical fields, tests pass, and real 20260330 dry-run lands on `reversal_day`.
  - Blocking: None.
- [x] P1: Run strict validation and sync final session/context metadata.
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passes and handoff/meta contain final evidence.
  - Blocking: None.
- [ ] P2: Backfill historical cold artifacts onto the canonical v3 archive contract.
  - Owner: Codex
  - Definition of Done: controlled rerun updates historical daily/by_regime manifests and quality reports under the new schema.
  - Blocking: Requires a separate execution window to avoid mixing rollout with implementation.

## Parking Lot
- [ ] Decide whether compatibility consumers should eventually read `legacy_primary_tag` or be migrated directly to `primary_day_type`.
- [ ] Decide whether to regenerate only recent dates or the full historical cold archive set in the backfill session.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Strict validation passed and session/context evidence were synchronized. (2026-03-31 01:51 ET)
- [x] Cut over EOD classifier output to canonical taxonomy fields. (2026-03-31 01:44 ET)
- [x] Updated regression tests to enforce canonical fields plus legacy mapping behavior. (2026-03-31 01:46 ET)
- [x] Verified real `20260330` dry-run output as `reversal_day / mid_close / legacy=unclassified`. (2026-03-31 01:45 ET)

# Open Tasks

## Priority Queue
- [x] P0: Backfill all backfillable historical cold manifests onto the canonical day-taxonomy contract.
  - Owner: Codex
  - Definition of Done: every date with complete `research/raw|feature|label` sources rewrites `data/cold/daily`, `data/cold/reports`, and `data/cold/by_regime` under canonical fields, and stale flat `by_regime` date entries are removed.
  - Blocking: None.
- [x] P1: Run strict validation and sync final session/context metadata.
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passes and all session/context files record the exact result.
  - Blocking: None.
- [ ] P2: Decide how to resolve legacy-only dates `20260311/12/13/17` that no longer have `research/raw` source files.
  - Owner: Codex
  - Definition of Done: either recover the missing raw sources and rebuild canonical manifests, or explicitly retire those legacy manifests with documented provenance limits.
  - Blocking: `data/research/raw/raw_20260311.parquet`, `raw_20260312.parquet`, `raw_20260313.parquet`, and `raw_20260317.parquet` are absent.

## Parking Lot
- [ ] Decide whether a dedicated backfill utility script is worth adding, or keep future reruns as controlled session commands.
- [ ] Decide whether `20260324` should be treated as newly archived history or folded into a broader historical completeness audit.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Strict validation passed and session/context evidence were synchronized. (2026-03-31 02:00 ET)
- [x] Previewed canonical archive reruns for `20260324/25/26/27/30` before touching production `data/cold`. (2026-03-31 01:55 ET)
- [x] Backfilled production cold manifests for all backfillable dates and removed stale flat `by_regime` date entries for affected sessions. (2026-03-31 01:56 ET)
- [x] Verified post-backfill manifest sync for `20260324/25/26/27/30`. (2026-03-31 01:56 ET)

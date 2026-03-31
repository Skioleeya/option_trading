# Open Tasks

## Priority Queue
- [x] P0: Hard-cut the canonical day-taxonomy contract with no compatibility aliases and no rollback path in active cold outputs.
  - Owner: Codex
  - Definition of Done: classifier return payload, daily manifest, by-regime manifest, and quality report expose only canonical fields; active cold archive contains no legacy flat-label manifests.
  - Blocking: None.
- [x] P1: Run strict validation and sync final session/context metadata.
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passes and all session/context files record the exact result.
  - Blocking: None.
- [ ] P2: If pre-20260324 history is ever needed again, recover missing `research/raw` sources and rebuild those dates directly into the canonical contract.
  - Owner: Codex
  - Definition of Done: retired days are restored only via canonical manifests, never via legacy flat-label artifacts.
  - Blocking: `data/research/raw/raw_20260311.parquet`, `raw_20260312.parquet`, `raw_20260313.parquet`, and `raw_20260317.parquet` are absent.

## Parking Lot
- [ ] Decide whether to stamp a new archive contract version string after the hard cut, or keep `v3` as the canonical-only contract.
- [ ] Decide whether retired historical dates should be tracked in a dedicated tombstone manifest.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Strict validation passed and session/context evidence were synchronized. (2026-03-31 02:15 ET)
- [x] Removed legacy compatibility fields from classifier and archive outputs. (2026-03-31 02:10 ET)
- [x] Updated OpenSpec day-taxonomy proposal/design/spec/tasks to require hard cut semantics. (2026-03-31 02:10 ET)
- [x] Rewrote active cold archive to canonical-only manifests and retired legacy-only dates `20260311/12/13/17`. (2026-03-31 02:12 ET)
- [x] Verified active `data/cold` no longer contains legacy fields and synced canonical manifests successfully. (2026-03-31 02:12 ET)

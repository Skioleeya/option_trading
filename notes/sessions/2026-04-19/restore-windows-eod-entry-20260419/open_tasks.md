# Open Tasks

## Priority Queue
- [x] P0: Restore missing Windows EOD task entry script `scripts/ops/run_eod_bucket.ps1`.
  - Owner: Codex
  - Definition of Done: Script exists, resolves repo root, calls `manage.py run-eod-bucket`, and returns child exit code.
  - Blocking: none
- [x] P1: Capture verification evidence and strict-gate output in session records.
  - Owner: Codex
  - Definition of Done: `meta.yaml` and `handoff.md` include executed commands and results.
  - Blocking: none
- [x] P2: Confirm no unintended runtime-layer code changes.
  - Owner: Codex
  - Definition of Done: Diff limited to `scripts/ops` and `notes/` session/context files.
  - Blocking: none

## Parking Lot
- [x] Item: none

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Session bootstrap and context pointer switch completed (2026-04-19 17:41 ET)
- [x] Windows EOD entry script restored (2026-04-19 17:44 ET)

# Open Tasks

## Priority Queue
- [x] P0: hard-cut governance contract from WSL/Linux to Windows-only and normalize mandatory command entry to `python manage.py`. (2026-04-22 11:22 ET)
  - Owner: Codex
  - Definition of Done: AGENTS/SOP/scripts docs contain Windows-only runtime contract and no active `python3 manage.py` directive.
  - Blocking: none
- [x] P0: replace Linux-only ops dependencies in active CLI paths (`pgrep/pkill/findmnt/systemd/.venv/bin`) with Windows-native implementation. (2026-04-22 11:23 ET)
  - Owner: Codex
  - Definition of Done: `start-backend/start-all/redis_preflight/register-eod-bucket-task/validate-session` execute on Windows contract without compatibility branch.
  - Blocking: none
- [x] P1: align regression/policy artifacts for the hard cut. (2026-04-22 11:24 ET)
  - Owner: Codex
  - Definition of Done: relevant tests and policy parser updated for `python manage.py` contract and Windows Redis owner semantics.
  - Blocking: host ACL issue prevents pytest tmp fixture creation (recorded in handoff).

## Parking Lot
- [x] none

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Updated AGENTS hard hooks and runtime constraints to Windows-only + `python manage.py` command contract. (2026-04-22 11:20 ET)
- [x] Hard-cut ops runtime modules (`start_backend/start_all/redis_preflight/eod/validate_session`) to Windows-native behavior without fallback. (2026-04-22 11:23 ET)
- [x] Updated SOP pack command snippets and Redis owner contract to NTFS fixed-drive policy. (2026-04-22 11:22 ET)
- [x] Added/updated regression coverage in `infra/ops_cli/test_start_all.py` for Windows Redis owner contract. (2026-04-22 11:23 ET)

# Open Tasks

## Priority Queue
- [x] P0: Diagnose why the 09:25 scheduled task opened CMD but did not leave the system stack running.
  - Owner: Codex
  - Definition of Done: identify whether scheduler timeout, repo timeout, or backend strict startup caused exit.
  - Blocking: None
- [x] P0: Add finite retry to the scheduled pre-open strict startup path.
  - Owner: Codex
  - Definition of Done: trading-day `start-all` failures retry with bounded attempts; non-trading guard remains single-attempt shutdown.
  - Blocking: None

## Parking Lot
- Operational follow-up: after this change is applied, run `.\.venv\Scripts\python.exe manage.py register-start-all-task --apply` on the Windows host so the installed task uses the retry-aware command.
- Operational follow-up: capture next 09:25 scheduled startup evidence and confirm whether the first attempt succeeded or retry was used.
- Consider whether LongPort startup probe should expose SDK timeout diagnostics separately from retry attempts.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Found 2026-07-10 09:25 backend failure in `logs/backend_runtime.current.log`: `QuoteContext init failed: request timeout`, followed by strict application startup failure. (2026-07-10 10:10 ET)
- [x] Added scheduled startup retry policy and regression coverage. (2026-07-10 10:32 ET)

# Open Tasks

## Priority Queue
- [x] P0: Register `start-all` as a Windows pre-open scheduled task with trading-day guard.
  - Owner: Codex
  - Definition of Done: `register-start-all-task --apply` installs a 09:25 ET weekday task and `run-scheduled-start-all` shuts the stack back down after launch when the ET date is not an `XNYS` session.
  - Blocking: None
- [x] P1: Restore the standard `start-all` path after the Python 3.12 environment drift and LongPort config incompatibility.
  - Owner: Codex
  - Definition of Done: `manage.py start-all` returns success with Redis, backend, and frontend all healthy.
  - Blocking: None
- [x] P2: Decided to keep the current pre-open task in `Interactive only` mode unless the operator later explicitly wants stored-credential execution.
  - Owner: Lenovo + Codex
  - Definition of Done: current host task contract is documented and no longer blocks automatic pre-open launch for logged-in desk operation.
  - Blocking: None

## Parking Lot
- [x] Considered whether the pre-open task should emit a dedicated scheduler log file under `tmp/schtasks/` for simpler Windows-side forensics; deferred as a later enhancement.
- [x] Considered adding a matching scheduled stop/teardown contract after market close; deferred outside this startup-automation session.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added `run-scheduled-start-all` and `register-start-all-task` for pre-open automatic startup. (2026-07-09 13:40 ET)
- [x] Installed `OptionV4-StartAll-PreOpen` and verified `Next Run Time: 7/10/2026 9:25:00 AM`. (2026-07-09 13:39 ET)
- [x] Verified holiday auto-shutdown (`2026-07-04`) and trading-day keep-running (`2026-07-09`) paths for the new scheduler command. (2026-07-09 14:00 ET)

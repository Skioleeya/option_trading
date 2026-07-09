# Open Tasks

## Priority Queue
- No active session-local tasks. The host startup and health verification is complete.

## Parking Lot
- None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Created a dedicated session for the 2026-04-23 real-host `start-all` verification and switched the context pointers. (2026-04-23 07:45 ET)
- [x] Started Redis, backend, and frontend via the standard Windows host entrypoint `.\.venv\Scripts\python.exe manage.py start-all`. (2026-04-23 07:46 ET)
- [x] Verified backend health, frontend HTTP health, same-origin `/api` proxy health, and same-origin `/ws/dashboard` streaming health on the host. (2026-04-23 07:49 ET)
- [x] Reviewed Redis/backend/frontend runtime evidence and recorded the outcome for handoff. (2026-04-23 07:52 ET)

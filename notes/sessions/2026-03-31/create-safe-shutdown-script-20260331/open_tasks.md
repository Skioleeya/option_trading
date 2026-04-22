# Open Tasks

## Parking Lot
- [ ] If you later want service-aware shutdown, extend the script to stop repo-managed backend/frontend processes before scheduling OS shutdown.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added a root-level safe shutdown PowerShell script with confirmation, delay, and abort support. (2026-03-31 09:49 ET)
- [x] Verified `safe_shutdown.ps1` with parse-only and `-WhatIf` dry-run checks. (2026-03-31 10:38 ET)
- [x] Passed `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`. (2026-03-31 10:39 ET)

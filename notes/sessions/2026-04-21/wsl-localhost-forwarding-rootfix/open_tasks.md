# Open Tasks

## Priority Queue
- [x] P0: Prove whether the Windows browser failure was a frontend service outage or a WSL localhost-forwarding failure.
  - Owner: Codex
  - Definition of Done: Windows localhost fails while WSL-IP path succeeds, proving the service is up and the forwarding layer is the broken owner.
  - Blocking: none
- [x] P0: Restore Windows `localhost:5173` access.
  - Owner: Codex
  - Definition of Done: after owner correction, Windows `localhost:5173` and `127.0.0.1:5173` return `200` and `python3 manage.py start-all` passes on the real host.
  - Blocking: none
- [x] P1: Write the WSL default-distro / localhost-forwarding contract into the startup SOP.
  - Owner: Codex
  - Definition of Done: startup doc states that `Ubuntu` must remain the default WSL distro owner and documents the hard recovery path.
  - Blocking: none

## Parking Lot
- [ ] Determine why Windows `127.0.0.1:8001` remained inconsistent even though `172.18.106.33:8001` and WSL-local `/health` were healthy; this is outside the browser contract because direct backend browsing is forbidden.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Restored Windows browser access to `localhost:5173` by correcting the WSL default distro owner and rebooting the host (2026-04-21 19:27 ET)

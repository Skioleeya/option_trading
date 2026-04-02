# Open Tasks

## Priority Queue
- [ ] P1: identify the next zero-hit leaf set outside `config_cloud_ref/*`
  - Owner: Codex
  - Definition of Done:
    - next Wave 0 allowlist is generated and verified
  - Blocking: must maintain the same strict zero-hit criteria
- [ ] P1: begin Wave 1 contracts/models Rust replacement
  - Owner: Codex
  - Definition of Done:
    - first contract/model owner group has a Rust single-source replacement and corresponding Python deletion plan
  - Blocking: requires a dedicated implementation slice

## Parking Lot
- [ ] decide whether the active spec reference to `shared/config_cloud_ref/agent_g.py` should be retired so the last cloud-ref file can be deleted later
- [ ] classify `shared/cache/oi_snapshot.py` as runtime owner vs later Rust replacement leaf

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Deleted 9 zero-hit dead leaves from `shared/config_cloud_ref/*` under Wave 0 criteria (2026-04-01 13:22 ET)

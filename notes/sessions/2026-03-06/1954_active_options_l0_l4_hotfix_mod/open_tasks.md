# Open Tasks

## Priority Queue
- [x] P0: Restore ActiveOptions L3->L4 field contract for `impact_index`/`is_sweep`.
  - Owner: Codex
  - Definition of Done: L3 typed rows and serialized `ui_state.active_options[*]` include `impact_index` and `is_sweep`.
  - Blocking: None
- [x] P1: Normalize ActiveOptions `option_type` in L3 adapters.
  - Owner: Codex
  - Definition of Done: Inputs `C|P|CALL|PUT` are emitted as `CALL|PUT`.
  - Blocking: None
- [x] P1: Modularize L4 ActiveOptions input normalization.
  - Owner: Codex
  - Definition of Done: `activeOptionsModel` added and `ActiveOptions.tsx` consumes normalized rows only.
  - Blocking: None
- [x] P1: Add focused regression coverage for ActiveOptions contract and model.
  - Owner: Codex
  - Definition of Done: focused pytest + vitest targets green.
  - Blocking: None

## Parking Lot
- [x] None (this session)

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] ActiveOptions L0-L4 hotfix + modularization completed (2026-03-06 20:00 ET)

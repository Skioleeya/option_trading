# Open Tasks

## Priority Queue
- [x] P0: Re-verify current L0 LongPort option field alignment against runtime code and tests
  - Owner: Codex
  - Definition of Done: The field dictionary matches actual L0 runtime contracts for `option_quote`, `option_chain_info_by_date`, and `calc_indexes`.
  - Blocking: None
- [ ] P1: Decide whether preserved-but-unused L0 fields should enter downstream diagnostics
  - Owner: Codex
  - Definition of Done: Team decision recorded for `trade_status`, `historical_volatility`, `standard`, `premium`, and related preserved fields.
  - Blocking: Product/architecture prioritization
- [ ] P2: Observe one live runtime after rebuild to validate preserved official LongPort fields against real payloads
  - Owner: Codex
  - Definition of Done: Live observation confirms `option_extend`, `standard`, and normalized aliases remain consistent in runtime logs.
  - Blocking: Requires rebuilt/loaded runtime and live session

## Parking Lot
- [ ] Consider adding a smaller “preserved vs consumed” table into `docs/SOP/L0_DATA_FEED.md` if this distinction becomes operationally important.
- [ ] If live payloads differ from official examples, append an evidence addendum for `expiry_date` and IV raw format.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Updated `docs/LONGPORT_OPTION_FIELD_DICTIONARY.md` from verified L0 code and tests (2026-03-12 14:19 ET)

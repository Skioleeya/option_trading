# Open Tasks

## Priority Queue
- [x] P0: Implement Phase D light research metrics
  - Owner: Codex
  - Definition of Done:
    - `realized_volatility_15m` and `vrp_realized_based` are available in L2 optional/research feature paths.
    - research feature store persists dual-track skew/VRP columns explicitly.
    - targeted tests and SOP/OpenSpec task records are updated.
  - Blocking: None
- [ ] P1: Decide official LongPort volatility field adoption vs local realized-vol path
  - Owner: Codex
  - Definition of Done:
    - Review whether `historical_volatility/premium/standard` should feed research/runtime paths.
    - Document whether local rolling RV remains canonical research source or becomes fallback.
  - Blocking: Requires product/data-priority decision.
- [ ] P2: Plan L3/L4 alias retirement for `net_charm` / `net_vanna`
  - Owner: Codex
  - Definition of Done:
    - Audit typed presenter/UI consumption and define deprecation window.
    - Ensure any visible rename is coordinated with presenter/model expectations.
  - Blocking: Downstream presentation code currently hard-depends on `net_charm`.

## Parking Lot
- [ ] Consider exposing realized-vol window length via config once research users request horizon tuning.
- [ ] Consider adding dedicated research docs for official LongPort vol fields after the data-priority decision.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Phase D light implementation and targeted regression pass (2026-03-12 15:04 ET)

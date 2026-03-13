# Open Tasks

## Priority Queue
- [x] P0: Execute Phase B skew/raw-exposure contract convergence
  - Owner: Codex
  - Definition of Done:
    - `rr25_call_minus_put` is emitted alongside legacy `skew_25d_normalized`.
    - `net_vanna_raw_sum` / `net_charm_raw_sum` are canonical in L1/L2/research contracts with legacy aliases preserved.
    - Targeted L1/L2/research regressions pass and SOP wording is synchronized.
  - Blocking: None
- [ ] P1: Decide Phase D sequencing for official LongPort vol fields vs new derived research metrics
  - Owner: Codex
  - Definition of Done:
    - Confirm whether `historical_volatility/premium/standard` should enter runtime/research contracts before new derived fields.
    - Reflect the decision in OpenSpec sequencing and next implementation scope.
  - Blocking: Requires product/research priority confirmation.
- [ ] P2: Review whether L3/L4 should adopt canonical raw-sum labels in typed contracts after alias window
  - Owner: Codex
  - Definition of Done:
    - Scan `payload_assembler` / UI typed models for direct `net_charm` or `net_vanna` label exposure.
    - Decide deprecation timeline for legacy aliases.
  - Blocking: Depends on downstream consumer appetite for a visible contract rename.

## Parking Lot
- [ ] Consider extending L3 research/history projection docs once Phase D scope is chosen.
- [ ] Consider updating non-SOP audit/sourcebook docs beyond `docs/IV_METRICS_MAP.md` if those documents become operator-facing.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Phase B implementation and regression pass (2026-03-12 14:50 ET)

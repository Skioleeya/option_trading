# Open Tasks

## Priority Queue
- [x] P0: verify live ActiveOptions `VOL` values and ordering online.
  - Owner: Codex
  - Definition of Done: online diagnostics, websocket evidence, and repository verification script all agree that `VOL` is bounded, present, and ordered according to the live contract.
  - Blocking: none
- [x] P1: classify why live regular-hours ActiveOptions still sustains synthetic fallback rows after the `VOL` field itself was validated as healthy.
  - Owner: Codex
  - Definition of Done: root cause identifies whether sparse real winners come from source chain sparsity, filter thresholds, or runtime selection cadence.
  - Blocking: none
- [ ] P1: capture a raw chain vs displayed-top5 comparison artifact for one sparse live window.
  - Owner: Codex
  - Definition of Done: one saved artifact shows candidate volumes/turnover/open-interest next to displayed rows for the same source version.
  - Blocking: live sparse window timing
- [ ] P2: run a bounded A/B check on `FLOW_ACTIVE_MIN_VOLUME` to confirm whether sparse windows are mostly policy-driven rather than source-decoding failures.
  - Owner: Codex
  - Definition of Done: one controlled run shows whether lowering the threshold materially increases non-synthetic winners without masking a deeper source issue.
  - Blocking: requires a controlled runtime verification window

## Parking Lot
- [ ] Compare `filtered_candidates_count` against displayed synthetic row count over a longer regular-hours window.
- [ ] Decide whether health/ops scripts should expose `rows_real_non_synthetic` directly in the PASS line.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Confirmed `/health` and `/debug/persistence_status` were live and advancing, with `active_options_total=5`, `real=5`, `missing_turnover_rows=0`, and repeated partial-fallback counters visible (2026-03-26 13:32 ET)
- [x] Sampled websocket ActiveOptions payloads and confirmed `VOL` stayed sorted descending with no negative or implausible values in the observed live window (2026-03-26 13:34 ET)
- [x] Ran `scripts/ops/verify_active_options_hotfix.ps1` and confirmed the existing online verification gate still passes (2026-03-26 13:35 ET)
- [x] Re-ran `shared/services/active_options/test_runtime_service.py -q` and confirmed the `current_volume` fallback, implausible-volume clamp, and VOL-order coverage remained green (2026-03-26 13:35 ET)
- [x] Classified the sparse-window root cause as threshold/candidate-pool driven rather than transport outage: current logs show both `filtered_candidates_count=2` partial fallback and fully empty `No options above min_volume threshold` fallback under `threshold=100` (2026-03-26 13:45 ET)
- [x] Identified the 3-tick switch gate as a secondary display artifact: diagnostics can already be empty-filter while the payload still holds one older real row pending signature confirmation (2026-03-26 13:45 ET)

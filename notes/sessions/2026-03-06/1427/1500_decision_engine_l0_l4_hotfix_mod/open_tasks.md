# Open Tasks

## Priority Queue
- [x] P0: Hotfix DecisionEngine `HALT` / IV-regime alias color-contract break.
  - Owner: Codex
  - Definition of Done: `HALT`, `LOW_VOL`, `HIGH_VOL` no longer produce undefined style classes and render stable semantic colors.
  - Blocking: None
- [x] P1: Modularize DecisionEngine state/color/weight normalization with tests.
  - Owner: Codex
  - Definition of Done: Pure model module extracted, unit tests added, regression tests/build pass.
  - Blocking: None
- [x] P1: Hotfix `TrapDetector` exit hysteresis (`k_exit`) for TRAPS indicator stability.
  - Owner: Codex
  - Definition of Done: Active trap state no longer exits on first non-confirm tick after activation; covered by unit test.
  - Blocking: None
- [x] P0: Hotfix DecisionEngine fused-signal regime/intensity contract hardcoding.
  - Owner: Codex
  - Definition of Done: `fused_signal.regime` / `gex_intensity` carry runtime values instead of `NORMAL/NEUTRAL` constants; backend tests enforce contract.
  - Blocking: None
- [x] P1: Modularize fused-signal contract parsing/classification.
  - Owner: Codex
  - Definition of Done: Shared helper module handles iv-regime normalization + gex-intensity classification and is used by DecisionOutput/Reactor.
  - Blocking: None
- [x] P1: Fix DecisionEngine regime badge text formatting and moderate-tone mapping.
  - Owner: Codex
  - Definition of Done: No per-letter split labels (`N E U T R A L`), `MODERATE` badge has explicit color token, tests added.
  - Blocking: None
- [x] P0: Hotfix FeatureStore snapshot-version cache invalidation for IV realtime integrity.
  - Owner: Codex
  - Definition of Done: new snapshot `version` no longer reuses stale TTL cache values (`atm_iv`, `iv_velocity_1m`, etc.); regression tests lock behavior.
  - Blocking: None
- [x] P1: Modularize FeatureStore cache policy into testable helpers.
  - Owner: Codex
  - Definition of Done: cache-hit, version extraction, and invalidation logic split into internal helpers with dedicated tests.
  - Blocking: None
- [ ] P2: Add component render-level regression for momentum/traps semantics (`weight` vs `conf`) and `HALT`/`iv_regime` visual paths.
  - Owner: Next agent
  - Definition of Done: RTL/Vitest asserts key classes and labels when payload contains `HALT` and `HIGH_VOL/LOW_VOL`, and ensures momentum/traps cards show weight and confidence as distinct signals.
  - Blocking: None

## Parking Lot
- [ ] Evaluate whether `DecisionEngine` should display `regime/gex_intensity` from stronger L2 metadata instead of current fallback values.
- [ ] Consider extracting right-panel color token resolver shared by `DecisionEngine` and `MtfFlow`.

## Completed (Recent)
- [x] Fixed major HALT/IV-regime style mapping bug in `DecisionEngine` (2026-03-06 14:33 ET)
- [x] Added `decisionEngineModel` modular helper and unit tests (2026-03-06 14:33 ET)
- [x] Fixed `TrapDetector` `k_exit` state-machine bug for TRAPS stability (2026-03-06 14:40 ET)
- [x] Fixed L2 fused-signal `regime/gex_intensity` hardcoding by runtime contract derivation (2026-03-06 15:03 ET)
- [x] Fixed DecisionEngine regime badge formatter + added moderate gex badge token path (2026-03-06 15:03 ET)
- [x] Fixed FeatureStore version-cache bug causing stale IV features under high-frequency snapshots (2026-03-06 15:20 ET)

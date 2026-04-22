# Open Tasks

## Priority Queue
- [x] P0: Pass strict validation for Wave1 (A+B)
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` passes and session/context evidence is written.
  - Blocking: none
- [x] P1: Complete `impl-20260403-l1-streaming-aggregator-bridge-marshalling-audit`
  - Owner: Codex
  - Definition of Done: `streaming_aggregator` 去掉冗余 NumPy marshalling，并完成 flip-level Rust owner 收口。
  - Blocking: none
- [x] P2: Complete `impl-20260403-l1-greeks-engine-bridge-marshalling-audit`
  - Owner: Codex
  - Definition of Done: `greeks_engine` live 路径切断 `bsm_fast` 伪 bridge，经中立服务直达 Rust owner，且无 fallback。
  - Blocking: none

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] `StreamingAggregator` 去冗余 marshalling，并将 `flip_level_cumulative` owner 收口到 Rust payload（2026-04-03 09:29 ET）
- [x] `GreeksEngine` 移除 `bsm_fast` live 依赖，改由 `shared.services.greeks_engine_batch` 进入 Rust owner（2026-04-03 09:30 ET）
- [x] Wave1 A+B strict gate 通过（2026-04-03 09:31 ET）

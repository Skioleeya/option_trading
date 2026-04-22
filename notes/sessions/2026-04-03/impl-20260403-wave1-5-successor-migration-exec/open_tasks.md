# Open Tasks

## Priority Queue
- [x] P0: Execute `impl-20260403-l2-attention-fusion-rust`
  - Owner: Codex
  - Definition of Done: attention fusion numerical core migrated to Rust owner and NumPy runtime compute removed.
  - Blocking: none
- [x] P1: Execute `impl-20260403-l1-wall-context-rust`
  - Owner: Codex
  - Definition of Done: wall-context numerical owner moved to Rust with Arrow-first RecordBatch path.
  - Blocking: none
- [x] P2: Strict validation and session/context sync
  - Owner: Codex
  - Definition of Done: `scripts/validate_session.ps1 -Strict` pass and evidence synced.
  - Blocking: none

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Added Rust owner `compute_attention_fused` and retargeted `attention_fusion.py` (2026-04-03 09:49 ET)
- [x] Added Rust wall-context helpers and retargeted `wall_context_builder.py` (2026-04-03 09:50 ET)
- [x] Added targeted bridge tests for L1/L2 successor migrations (2026-04-03 09:51 ET)
- [x] Resolved subagent quality findings: removed residual L1 Python arithmetic bridge logic + added `DecisionOutput.data["fused_signal"]` contract assertions (2026-04-03 10:07 ET)
- [x] Strict gate passed for Wave 1.5 session (2026-04-03 09:53 ET)

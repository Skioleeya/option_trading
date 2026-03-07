# Open Tasks

## Priority Queue
- [x] P0: Remove direct `l2_decision -> l3_assembly` dependency (AgentG no longer imports/owns L3 ActiveOptions presenter).
  - Owner: Codex
  - Definition of Done: `l2_decision/agents/agent_g.py` contains no `l3_assembly` import and no `_active_options_presenter` state.
  - Blocking: None
- [x] P0: Remove direct `l3_assembly -> l2_decision` dependency for ActiveOptions runtime (moved to neutral shared service).
  - Owner: Codex
  - Definition of Done: Flow/DEG runtime moved to `shared/services/active_options/*`; L3 ActiveOptions presenter wrapper only references shared service.
  - Blocking: None
- [x] P0: Remove orchestration-layer private-member access for ActiveOptions path.
  - Owner: Codex
  - Definition of Done: `app/loops/*` use `ctr.active_options_service` public API; no `ctr.agent_g._active_options_presenter` usage remains.
  - Blocking: None
- [x] P1: Retire `USE_L2` legacy toggle and enforce L1->L2->L3 runtime chain.
  - Owner: Codex
  - Definition of Done: `app/container.py` no longer exposes `USE_L2`; compute/lifespan follow single pipeline path.
  - Blocking: None
- [x] P1: Sync architecture guardrail + SOP docs for behavior-level change.
  - Owner: Codex
  - Definition of Done: `scripts/policy/layer_boundary_rules.json` and relevant `docs/SOP/*.md` updated in same session.
  - Blocking: None
- [x] P2: Execute required verification commands and capture pass/fail evidence.
  - Owner: Codex
  - Definition of Done: wrapper pytest commands recorded in handoff/meta with explicit failed-case notes.
  - Blocking: None

## Parking Lot
- [x] None

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] P0 reverse dependency cleanup + public service injection completed (2026-03-06 21:16 ET)

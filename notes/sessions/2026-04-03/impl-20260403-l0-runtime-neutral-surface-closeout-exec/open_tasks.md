# Open Tasks

## Priority Queue
- [x] P0: Sub-wave G fallback validation for l0 runtime
  - Owner: Codex
  - Definition of Done: Run the best available l0 runtime verification, capture pass/fail evidence, and record exact warnings/errors.
  - Blocking: Resolved in current Windows runtime; fallback path `pwsh scripts/test/run_pytest.ps1 scripts/test/test_l0_l4_pipeline.py` passed.
- [ ] P0: Sub-wave F dual-run evidence
  - Owner: Codex
  - Definition of Done: Capture a live 60-minute Python/Rust overlap or document the blocker with the next execution condition.
  - Blocking: Requires a live US market session with both gateways active; next executable window is 2026-04-03 09:30-16:00 ET.
- [x] P1: Sync OpenSpec child/parent task states and handoff evidence
  - Owner: Codex
  - Definition of Done: Update child and parent task files to match actual gate results and record the blocker/completion split.
  - Blocking: n/a

## Parking Lot
- [x] None.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Session bootstrap and active pointer switch completed (2026-04-03 03:56 ET)
- [x] Child/parent OpenSpec tasks synchronized to factual state（2026-04-03 04:03 ET）
- [x] OpenSpec chain naming violation fixed and `check_openspec_chain.py` re-run PASS（2026-04-03 04:13 ET）
- [x] Sub-wave G fallback validation passed via pytest wrapper（2026-04-03 04:25 ET）

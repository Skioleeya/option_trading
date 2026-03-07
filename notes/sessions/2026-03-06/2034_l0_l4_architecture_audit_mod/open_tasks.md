# Open Tasks

## Priority Queue
- [x] P0: Complete L0-L4 chain clarity and coupling audit with code-level evidence.
  - Owner: Codex
  - Definition of Done: Findings include concrete file/line references and risk grading.
  - Blocking: None
- [x] P1: Validate dependency direction assumptions (lower layers do not import upper layers).
  - Owner: Codex
  - Definition of Done: Confirmed `l0/l1` no reverse imports into `l2/l3/l4`; `l4` no backend imports.
  - Blocking: None
- [x] P1: Identify and document cross-layer coupling hotspots.
  - Owner: Codex
  - Definition of Done: Documented L2↔L3, L3↔L1, and app-loop private-member coupling points.
  - Blocking: None
- [x] P2: Record recommended decoupling roadmap (analysis-only, no behavior change).
  - Owner: Codex
  - Definition of Done: Next-step plan documented in handoff.
  - Blocking: None
- [x] P2: Create root-level execution checklist for decoupling program.
  - Owner: Codex
  - Definition of Done: `清单.md` exists at repository root with prioritized action items.
  - Blocking: None

## Parking Lot
- [x] None (this session)

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] L0-L4 architecture audit completed (2026-03-06 20:38 ET)

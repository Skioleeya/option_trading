# Open Tasks

## Priority Queue
- [x] P0: Restore `npm --prefix l4_ui run build`
  - Owner: Codex
  - Definition of Done: TypeScript build and targeted frontend tests are green without fallback typing hacks
  - Blocking: none
- [ ] P1: Re-run broader frontend test matrix if this branch is prepared for merge
  - Owner: Codex
  - Definition of Done: remaining non-targeted L4 suites are sampled after adjacent runtime work stabilizes
  - Blocking: unrelated concurrent branch churn in the same dirty worktree
- [ ] P2: none
  - Owner:
  - Definition of Done:
  - Blocking:

## Parking Lot
- [ ] Revisit whether `tsconfig.tsbuildinfo` should remain tracked or be normalized in repo tooling.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Replaced stale Node/file-string assertions with current contract tests for guardrails, triad, micro stats, ATM chart stream, and L4 RUM (2026-04-21 16:47 ET)
- [x] Restored strict frontend build with explicit `VITE_BACKEND_ORIGIN` and no compatibility branch (2026-04-21 16:47 ET)

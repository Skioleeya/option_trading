# Open Tasks

## Priority Queue
- [x] P0: Fix the 4 blocking `l4_ui` TypeScript build errors.
  - Owner: Codex
  - Definition of Done: `npm --prefix l4_ui run build` passes without TypeScript errors.
  - Blocking: None.
- [x] P1: Verify the affected modules still behave correctly.
  - Owner: Codex
  - Definition of Done: targeted tests pass for `mmFlowModel`, `ActiveOptions`, and `ProtocolAdapter`.
  - Blocking: None.
- [x] P2: Record strict validation evidence and sync indexes.
  - Owner: Codex
  - Definition of Done: `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` passes and is recorded in handoff.
  - Blocking: None.

## Parking Lot
- [ ] If future type tightening expands `DashboardPayload`, prefer explicit validators over broad interface assertions.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] `deltaDecoder` payload narrowing updated to return a validated `DashboardPayload` without unsafe direct cast (2026-04-17 16:52 ET)
- [x] `ActiveOptions` slot normalization typed as `ActiveOption[]` to preserve placeholder insertion compatibility (2026-04-17 16:52 ET)
- [x] `MmFlowCard` normalized optional metrics to `null` before view derivation (2026-04-17 16:52 ET)
- [x] `mmFlowModel` switched from `Record<string, number>` casting to explicit `MmFlowMetrics` construction (2026-04-17 16:52 ET)
- [x] `npm --prefix l4_ui run build` passed (2026-04-17 16:53 ET)
- [x] Targeted frontend tests passed (`3` files, `20` tests) (2026-04-17 16:53 ET)
- [x] Strict validation passed (2026-04-17 16:55 ET)

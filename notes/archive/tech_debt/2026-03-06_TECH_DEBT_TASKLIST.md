# Technical Debt Task List (Net Basis)

Date: 2026-03-06 (ET)  
Scope: `notes/sessions/2026-03-06/**/open_tasks.md`  
Accounting: net debt = 35 (raw 37 - 2 obsolete items)

## P0 (Do First)

- [x] T0-1: Harden L0-L4 timestamp contract (orig: P1)
  - Why: cross-layer timing mismatch can invalidate state/decision semantics.
  - DoD:
    - define single timestamp source + timezone contract in L0/L1/L3/L4;
    - add contract tests for parsing/propagation;
    - update SOP docs.
  - Done: completed in session `2026-03-06/1702/1702_p0_timestamp_atm_storage_hotfix_mod`.

- [x] T0-2: Reduce ATM decay storage write amplification (orig: P2)
  - Why: current append path does full `lrange + full-file rewrite` per tick (O(N^2) risk).
  - DoD:
    - replace with incremental append/mirror strategy;
    - benchmark under high tick load;
    - no data-loss on restart/recovery path.
  - Done: completed in session `2026-03-06/1702/1702_p0_timestamp_atm_storage_hotfix_mod`.

## P1 (Do Next)

- [x] T1-1: Add runtime observability probe for `snapshot_version` vs `spy_atm_iv` drift (orig: P2)
  - DoD: metric/log emits mismatch count + lag duration, visible in ops logs.
  - Done: completed in session `2026-03-06/1908_p1_probe_nav_chart_hotfix_mod`.

- [x] T1-2: ATM chart incremental update optimization (orig: P2 + Parking duplicate)
  - DoD: stop full `setData` on each tick where possible; keep render stable at 5k history.
  - Done: completed in session `2026-03-06/1908_p1_probe_nav_chart_hotfix_mod`.

- [x] T1-3: Resolve dead `l4:nav_*` command path (orig: P1)
  - DoD: command registry wiring works end-to-end and has integration test.
  - Done: completed in session `2026-03-06/1908_p1_probe_nav_chart_hotfix_mod`.

- [x] T1-4: Add `-NoPointerUpdate` mode to `scripts/new_session.ps1` (orig: duplicate P0)
  - DoD: session can be created without rewriting context pointers when explicitly requested.
  - Done: completed in session `2026-03-06/1908_p1_probe_nav_chart_hotfix_mod`.

## P2 (Process/Tooling Follow-up)

- [x] T2-1: Add `-Timezone` option in `scripts/new_session.ps1` (orig: P1)
  - Done: completed in session `2026-03-06/1818_p2_process_tooling_followup_mod`.
- [x] T2-2: Extend `validate_session.ps1 -Strict` (orig: P2)
  - Done: completed in session `2026-03-06/1818_p2_process_tooling_followup_mod`.
- [x] T2-3: Add CI hook / pre-merge job for session validation (orig: P2/Parking)
  - Done: completed in session `2026-03-06/1818_p2_process_tooling_followup_mod`.
- [x] T2-4: Harden workspace hygiene for generated runtime artifacts (orig: P2)
  - Done: completed in session `2026-03-06/1818_p2_process_tooling_followup_mod`.
- [x] T2-5: Add focused UI regression tests (DecisionEngine/Header/Debug hotkey paths).
  - Done: completed in session `2026-03-06/1818_p2_process_tooling_followup_mod`.

## Can Ignore (for Debt KPI)

These items should move to roadmap/UX backlog instead of debt KPI:

- visual session separators on ATM chart
- markdown link rendering for session pointers
- auto-generate session task-id from branch/timestamp
- right-panel color token refactor (if no bug/risk)
- binary ATM substream exploration tied to future protobuf migration

## Cleanup Action (Immediate)

- [x] Mark 2 obsolete items in historical session files with `SUPERSEDED-BY: <session-id>` to prevent debt inflation.
  - Done: `notes/sessions/2026-03-06/1908_p1_probe_nav_chart_hotfix_mod/open_tasks.md` updated for `T2-1/T2-2`.

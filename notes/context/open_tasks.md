# Open Tasks (Index)

## Active Session Tasks
- Path: notes/sessions/2026-03-06/2105_anti_coupling_guardrail_mod/open_tasks.md

## Global Backlog (Cross-Session)
- [x] P0: ATM decay storage append path O(N^2) fixed via JSONL append mirror (`SUPERSEDED-BY: 2026-03-06/1702/1702_p0_timestamp_atm_storage_hotfix_mod`).
- [x] P0: L0-L4 timestamp contract hardened with L0 `as_of_utc` source-of-truth (`SUPERSEDED-BY: 2026-03-06/1702/1702_p0_timestamp_atm_storage_hotfix_mod`).
- [x] P1: Add runtime observability probe for `snapshot_version` vs `spy_atm_iv` drift (`SUPERSEDED-BY: 2026-03-06/1908_p1_probe_nav_chart_hotfix_mod`).
- [x] P1: Resolve dead `l4:nav_*` command path (registry wiring + integration test) (`SUPERSEDED-BY: 2026-03-06/1908_p1_probe_nav_chart_hotfix_mod`).
- [x] P1: Add `new_session.ps1 -NoPointerUpdate` path for session bootstrap control (`SUPERSEDED-BY: 2026-03-06/1908_p1_probe_nav_chart_hotfix_mod`).
- [x] P2: ATM chart incremental render optimization at 5k history (`SUPERSEDED-BY: 2026-03-06/1908_p1_probe_nav_chart_hotfix_mod`).
- [x] P2: Add `new_session.ps1 -Timezone` with IANA/Windows support (`SUPERSEDED-BY: 2026-03-06/1818_p2_process_tooling_followup_mod`).
- [x] P2: Add strict gate to `validate_session.ps1` (`SUPERSEDED-BY: 2026-03-06/1818_p2_process_tooling_followup_mod`).
- [x] P2: Add pre-merge session validation CI workflow (`SUPERSEDED-BY: 2026-03-06/1818_p2_process_tooling_followup_mod`).
- [x] P2: Enforce runtime artifact hygiene in strict validation (`SUPERSEDED-BY: 2026-03-06/1818_p2_process_tooling_followup_mod`).
- [x] P2: Add focused UI regressions for DecisionEngine/Header/debug hotkey chain (`SUPERSEDED-BY: 2026-03-06/1818_p2_process_tooling_followup_mod`).

## Process
- Task details and completion evidence belong in the session-local open_tasks.md.
- Keep this file as the long-horizon queue and session pointer only.

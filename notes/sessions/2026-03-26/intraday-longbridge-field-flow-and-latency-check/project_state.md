# Project State

## Snapshot
- DateTime (ET): 2026-03-26 09:39:08 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `c279f847ce235dca5ad9fca3ec8617dca0f03f4e`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: audit intraday Longbridge/LongPort core field flow and freshness across L0 ingest, L1 compute, L3 payload continuity, ATM live continuity, and ActiveOptions live continuity.
- Scope In:
  - `/debug/persistence_status`, `/health`, `/api/atm-decay/history`, `ws://127.0.0.1:8001/ws/dashboard`, and `logs/backend_runtime.current.log`
  - field continuity for `rust_active`, `shm_stats`, `data_timestamp/timestamp`, `atm`, `atm_iv_context`, `depth_profile`, and `active_options`
  - pass/fail judgment for L0 runtime, L1 freshness, L3 payload continuity, ATM live continuity, and ActiveOptions live continuity
- Scope Out:
  - no runtime code changes
  - no SOP/OpenSpec updates because behavior is unchanged
  - no UI browser-console verification beyond backend WS/API evidence

## What Changed (Latest Session)
- Files:
  - `scripts/diag/audit_intraday_core_flow.py`
  - `notes/sessions/2026-03-26/intraday-longbridge-field-flow-and-latency-check/project_state.md`
  - `notes/sessions/2026-03-26/intraday-longbridge-field-flow-and-latency-check/open_tasks.md`
  - `notes/sessions/2026-03-26/intraday-longbridge-field-flow-and-latency-check/handoff.md`
  - `notes/sessions/2026-03-26/intraday-longbridge-field-flow-and-latency-check/meta.yaml`
  - `notes/context/handoff.md`
- Behavior:
  - captured a live intraday audit baseline showing L0 Arrow transport, L1 compute, L3 payload broadcast, root-level ATM payload, and ActiveOptions runtime are all currently advancing
  - added `scripts/diag/audit_intraday_core_flow.py` so operators can rerun the same core-chain audit with one command and receive subsystem-level `PASS/WARN/FAIL` output plus JSON evidence
  - confirmed the only active suppression is `snapshot_version_iv_probe.suppressed_reason=non_reactive_iv_source:rest`, which is diagnostic context rather than a runtime failure
  - performed a deeper ActiveOptions header/slot audit and confirmed the six visible columns (`SYM/T/STRIKE/IMP/VOL/FLOW`) carry structurally valid values, but the backend currently does not sustain five real contracts; it sustains five fixed slots with placeholders filling missing rows
- Verification:
  - sampled `/debug/persistence_status` three times over 10 seconds and observed advancing `l1_runtime.version`, `active_options_input.source_version`, and `stores.transport.last_batch_id`
  - sampled `ws://127.0.0.1:8001/ws/dashboard` and observed repeated `dashboard_delta` frames with `data_timestamp`, `version`, `atm`, `agent_g_ui_state`, and `signal`
  - sampled `/api/atm-decay/history?fields=timestamp,straddle_pct,call_pct,put_pct,strike_changed&schema=v2` and observed same-day ATM history continuing through the current intraday window
  - analyzed `logs/backend_runtime.current.log` with `scripts/diag/pull_backend_log_analysis.py` and observed `health=OK` with no rate-limit, cooldown, warm-up, or IV drift warnings
  - executed `python scripts/diag/audit_intraday_core_flow.py` and `python scripts/diag/audit_intraday_core_flow.py --json`, both returning overall `PASS`
  - sampled 30 websocket frames with merged `active_options` state and observed:
    - all frames preserved slots `1..5` with no missing or duplicate slot ids
    - all frames contained at least one placeholder row
    - slot 1 stayed pinned to `SPY|CALL|678.0` across all 30 frames
    - slots 2-4 churned between a small set of real puts and placeholders
    - slot 5 never held a real contract in the sampled window
    - no malformed values were observed in `symbol`, `option_type`, `strike`, `impact_index`, `flow_volume_label`, or `flow_deg_formatted`

## Risks / Constraints
- Risk 1: ATM IV freshness remains sourced from `rest`, so `snapshot_version` drift probing is intentionally suppressed and cannot be used as a websocket-latency failure signal in this window.
- Risk 2: this session audits current runtime state only; it does not prove future-session continuity if market conditions, provider cadence, or subscription composition change later in the day.
- Risk 3: ActiveOptions currently preserves five display slots but not five real contracts; placeholder occupancy is persistent and can mask depth of the live ranked set if operators assume all five rows are populated with real contracts.

## Next Action
- Immediate Next Step: keep `scripts/diag/audit_intraday_core_flow.py` as the standard rerun entrypoint, then trace why ActiveOptions currently sustains fewer than five real rows during this intraday window even though the fixed five-slot UI contract remains intact.
- Owner: Codex

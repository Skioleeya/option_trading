# Project State

## Snapshot
- DateTime (ET): 2026-03-27 09:37:34 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `6dfd9c5`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: restart the backend in the real external environment, verify live dataflow recovery, and isolate whether the empty-chain degradation was runtime code or launch-environment related.
- Scope In:
  - backend external restart path
  - broker connectivity probe in sandbox vs non-sandbox
  - live `/debug/persistence_status` verification
  - `notes/context/*`
  - `notes/sessions/2026-03-27/restart-backend-dataflow-repair-20260327/*`
- Scope Out:
  - no runtime code changes
  - no SOP or OpenSpec content changes
  - no frontend or strategy logic changes

## What Changed (Latest Session)
- Files:
  - `notes/context/project_state.md`
  - `notes/context/open_tasks.md`
  - `notes/context/handoff.md`
  - `notes/sessions/2026-03-27/restart-backend-dataflow-repair-20260327/project_state.md`
  - `notes/sessions/2026-03-27/restart-backend-dataflow-repair-20260327/open_tasks.md`
  - `notes/sessions/2026-03-27/restart-backend-dataflow-repair-20260327/handoff.md`
  - `notes/sessions/2026-03-27/restart-backend-dataflow-repair-20260327/meta.yaml`
- Behavior:
  - root cause investigation showed the prior empty-chain backend had been restarted inside the sandbox, so broker `/v2/socket/token` connectivity failed there and the runtime never produced the first `spot/subscription/Arrow writer` chain
  - the same Rust quote probe succeeded immediately when rerun outside the sandbox against both endpoint profiles
  - an external strict backend restart replaced the sandboxed instance and restored live runtime state on `8001`
  - live dataflow is now healthy: `gateway.connected=true`, `rust_started=true`, `transport.status=OK`, `chain_size=100`, `spot=639.885`, and L3 payloads are emitting `atm_status=LIVE`
- Verification:
  - sandbox probe reproduced dual endpoint failure for `/v2/socket/token`
  - external probe succeeded for both `primary` and `official_longbridge` profiles
  - external strict backend restart succeeded via `scripts/ops/start_backend.ps1`
  - `GET http://127.0.0.1:8001/health` returned `200`
  - `GET http://127.0.0.1:8001/debug/persistence_status` showed `version=2879`, `source_version=2879`, `tracked_symbols=100`, `last_batch_id=198`, `ws_price_seen=100`, and `transport.status=OK`
  - backend log now shows live `MarketEventBridge` streaming, GPU compute ticks, depth payload rows, and `atm_status=LIVE`

## Risks / Constraints
- Risk 1: this session proves the runtime is healthy only when launched outside the sandbox; sandbox-local restart commands still produce a false broker-connectivity failure and empty-chain degradation.
- Risk 2: `active_options` is now backed by real rows, but the flow engine still reports `DEGRADED` on the sampled rows because gamma inputs are missing for those contracts; this is separate from the transport outage and was not changed here.

## Next Action
- Immediate Next Step: sync this recovery evidence into handoff/context, rerun strict validation, and close out the strict fresh-launch backend backlog item as completed in this session.
- Owner: Codex

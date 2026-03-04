# Option_v3 — Agent Handoff Task List
**Last updated**: 2026-03-04 (post `v3.1-l1l2-cutover` tag)  
**Status**: L1+L2+L3+L4 wired. USE_L2=True in main.py. 292 tests passing.

---

## Context for Incoming Agent

- Git tag `v3.1-l1l2-cutover` = current HEAD (`57b3f9c`)
- **Rollback**: `USE_L2 = False` in `backend/app/main.py` instantly reverts to legacy `AgentG`
- Legacy files archived in `_legacy_backup/20260304/` (71 files + MANIFEST.md)
- Backend port: **8000** | L4 Frontend: **localhost:5173** | Redis port: **6380**
- **`atm_decay_tracker.py` is still in use** — not yet replaced

---

## P1 — This Week (Critical Path)

### [ ] 1. Start & Validate Backend at Market Open
```powershell
cd e:\US.market\Option_v3\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
After 60s, check:
```powershell
curl http://localhost:8000/debug/persistence_status
```
Verify: `agent_runner.running = true`, `l3_layer` non-empty, `redis.connected = true`

**Success criteria**: 1Hz broadcast stable, `[PERF] build_payload` log shows `agent=<500ms` consistently.

---

### [ ] 2. Verify L2 Audit Trail Writes to Parquet
`L2DecisionReactor` has `enable_audit_disk=True` by default but disk writer path needs validation.

```python
# Check in main.py after AppContainer.initialize_all():
container._l2_reactor.audit  # → should be an AuditDiskWriter instance
```

Expected: nightly `.parquet` file in `l2_refactor/audit/` or configured path.

---

### [ ] 3. Push to Remote after Validation
After 1 full trading day with no alerts:
```powershell
cd e:\US.market\Option_v3
git push origin master --tags
```

---

## P2 — This Week After Validation

### [ ] 4. Wire L0 Refactored Feed (Replaces OptionChainBuilder)
**Current gap**: `OptionChainBuilder` in `backend/app/services/feeds/` still serves as L0.  
The refactored `l0_refactor/` (MVCCChainStateStore, SanitizePipelineV2, StatisticalBreaker) is **not** yet wired.

**Prerequisites**: L1+L2 P99 latency < 200ms confirmed in live session.

**Steps**:
1. Read `l0_refactor/README.md` for integration API
2. In `backend/app/main.py`, add `L0_REFACTOR = False` feature flag (same pattern as `USE_L2`)
3. When `L0_REFACTOR=True`, replace `self.option_chain_builder.fetch_chain()` with `l0_refactor` feed adapter output
4. Verify `l0_refactor/feeds/LongportFeedAdapter` connects to existing `MarketDataGateway` WS credentials

---

### [ ] 5. Permanently Retire AgentG (Sunset USE_L2 Flag)
After 2-3 clean trading days with `USE_L2=True`:
1. Remove the `else: result = await self.agent_g.run(snapshot)` fallback branch in `_agent_runner_loop`
2. Remove `AgentG`, `AgentA`, `AgentB` imports from `main.py`
3. Set `USE_L2 = True` as hardcoded constant (remove the flag)
4. Run `python -m pytest l1_refactor/ l2_refactor/ l3_refactor/ -q` to confirm no regressions

---

## P3 — Next Week

### [ ] 6. Activate L2 Attention Fusion
Currently `L2DecisionReactor(use_attention_fusion=False)` — uses rule-based fusion only.

**Prerequisite**: ≥2 days of `DecisionAuditEntry` data accumulated.

**Steps**:
1. Extract historical `FeatureVector` records from Parquet audit logs
2. Run `l2_refactor/fusion/attention_fusion.py` calibration notebook
3. Change init to `L2DecisionReactor(use_attention_fusion=True)` in `main.py`
4. Shadow-run both modes for one session and compare `l2_reactor.shadow_stats()`

---

### [ ] 7. Set Up CI Gate (GitHub Actions)
No automated CI exists. All 292 tests are manual.

Create `.github/workflows/test.yml`:
```yaml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r backend/requirements.txt
      - run: |
          export LONGPORT_APP_KEY=dummy
          export LONGPORT_APP_SECRET=dummy  
          export LONGPORT_ACCESS_TOKEN=dummy
          python -m pytest l1_refactor/tests/ l2_refactor/tests/ l3_refactor/tests/ -q
```

---

### [ ] 8. L4 Frontend — Wire Real Alerts
`AlertEngine.ts` currently uses mock thresholds. Connect it to live L2 `guard_actions` events via WebSocket.

File: `l4_frontend/src/alerts/alertEngine.ts`  
Integration point: parse `agent_g.data.fused.guard_actions[]` from WS payload and trigger `alertStore.addAlert()`.

---

### [ ] 9. Monitoring Dashboard — SLO Alerts
Set up a `/metrics` Prometheus endpoint or structured logging:
- `l2_decision_latency_ms` histogram (P50/P95/P99)
- `l2_guard_action_total` counter by action type
- `l3_broadcast_latency_ms` gauge
- `l1_compute_latency_ms` histogram

---

## Architecture Reference

```
OptionChainBuilder (L0 legacy, still active)
    ↓ fetch_chain() dict
L1ComputeReactor.compute()          [l1_refactor/reactor.py]
    ↓ EnrichedSnapshot
L2DecisionReactor.decide()          [l2_refactor/reactor.py]  
    ↓ DecisionOutput.to_legacy_agent_result()
L3AssemblyReactor.tick()           [l3_refactor/reactor.py]
    ↓ FrozenPayload → BroadcastGovernor
L4 Frontend Zustand store           [l4_frontend/src/store/dashboardStore.ts]
```

**Key files for any agent starting work**:
- `backend/app/main.py` — wiring hub, all feature flags here
- `l2_refactor/events/decision_events.py` — L2→L3 contract
- `l3_refactor/events/payload_events.py` — L3→L4 contract
- `_legacy_backup/20260304/MANIFEST.md` — what every legacy file was replaced by

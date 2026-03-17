## Phase 1 Baseline Evidence

Collected at: `2026-03-17 16:40` (US/Eastern)

### 1) min_volume trigger baseline (live console source)

Command:

```powershell
python scripts/diag/pull_backend_log_analysis.py --source console --lines 400 --json
```

Observed:

- `requested_lines`: `400`
- `line_count`: `34` (console visible rows)
- `no_options_warn_hits`: `15`
- `sabr_no_data_hits`: `2`
- `iv_drift_hits`: `6`
- `max_lag_seconds`: `1227.984`
- `rate_limit_301607_hits`: `0`
- `global_cooldown_hits`: `0`

Interpretation:

- Active Options placeholder branch is frequently triggered in the observed window.
- Runtime is not in API cooldown/301607 state in this sample.

### 2) runtime counters baseline (`/debug/persistence_status`)

Command:

```powershell
Invoke-WebRequest http://127.0.0.1:8001/debug/persistence_status
```

Observed key fields:

- `chain_size`: `352`
- `version`: `106828`
- `spot`: `670.79`
- `ws_volume_seen`: `352`
- `ws_current_volume_seen`: `0`
- `ws_turnover_seen`: `0`
- `volume_map_size`: `121`
- `pending_warmup_symbols`: `0`
- `limiter_profile`: `steady`
- `cooldown_active`: `false`
- `iv_probe_lag_seconds`: `1227.984`

Interpretation:

- Subscription pool is populated (`chain_size=352`), but `current_volume/turnover` WS seen counters are zero.
- This is consistent with downstream inability to leverage `current_volume` fallback semantics.

### 3) Arrow schema field baseline

Command:

```powershell
python - <<'PY'
from l1_compute.arrow.schema import OPTION_CHAIN_SCHEMA
print(OPTION_CHAIN_SCHEMA.names)
PY
```

Observed fields:

- `symbol`
- `strike`
- `is_call`
- `bid`
- `ask`
- `iv`
- `volume`
- `open_interest`
- `contract_multiplier`

Gap snapshot:

- `current_volume` is absent.
- `turnover` is absent.

### 4) Target / Non-target freeze (Phase 1 scope evidence)

Target files (Top N):

1. `l1_compute/arrow/schema.py`
2. `app/loops/housekeeping_loop.py`
3. `shared/services/active_options/runtime_service.py`
4. `l1_compute/tests/test_arrow.py`
5. `app/loops/tests/test_housekeeping_gpu_dedup.py`

Non-target:

- `l2_decision/*`
- `l3_assembly/*` (except contract consumers impacted by schema signature, if any)
- `l4_ui/*`
- network quota governor logic in `l0_ingest/feeds/rate_limiter.py`

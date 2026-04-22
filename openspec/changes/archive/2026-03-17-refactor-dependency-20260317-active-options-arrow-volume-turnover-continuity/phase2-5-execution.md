## Phase 2-5 Execution Evidence

Updated at: `2026-03-17 16:47` (US/Eastern)

## Phase 2 - Contract Mapping Freeze

### Frozen field semantics

- `volume`: cumulative/authoritative volume field for Active Options filter and flow engines.
- `current_volume`: fallback volume source when `volume` is missing/zero.
- `turnover`: liquidity/flow magnitude field consumed by flow engines and ranking.

### Frozen fallback rule

- If `volume <= 0` and `current_volume > 0`, normalized row MUST set `volume = int(current_volume)`.
- No implicit rewrite of non-volume contract fields in this subproposal.

### Frozen non-target guarantee

- No changes in `l2_decision/*`, `l3_assembly/*`, `l4_ui/*`.
- No changes in rate limiter/governor control policy.

## Phase 3 - Arrow Contract Patch

Changed:

- `l1_compute/arrow/schema.py`
  - Added columns: `current_volume`, `turnover`
  - Updated `dicts_to_record_batch` mapping for both fields.

Verification:

```powershell
python - <<'PY'
from l1_compute.arrow.schema import OPTION_CHAIN_SCHEMA
print(OPTION_CHAIN_SCHEMA.names)
PY
```

Observed names:

- `symbol,strike,is_call,bid,ask,iv,volume,current_volume,turnover,open_interest,contract_multiplier`

## Phase 4 - Housekeeping Continuity

Changed:

- `app/loops/tests/test_housekeeping_gpu_dedup.py`
  - Added Arrow-style row test (`is_call + current_volume`) for normalization continuity.

Behavior confirmation:

- `_normalize_active_options_row` keeps deterministic `current_volume -> volume` fallback.
- Arrow rows (with `is_call`) are normalized to stable `option_type`.

## Phase 5 - Runtime Filter Consistency

Changed:

- `shared/services/active_options/runtime_service.py`
  - Added `_normalize_chain_volume_fields()`.
  - Applied pre-filter normalization before `min_volume` filter.
- `shared/services/active_options/test_runtime_service.py`
  - Added test: `volume=0 + current_volume>0` should pass filter and produce non-placeholder row.

Targeted regression run:

```powershell
.\scripts\test\run_pytest.ps1 l1_compute/tests/test_arrow.py app/loops/tests/test_housekeeping_gpu_dedup.py shared/services/active_options/test_runtime_service.py
```

Observed:

- `18 passed`

Live observability note:

- Console sample still shows frequent placeholder logs in the current market state (`no_options_warn_hits=14`), but this is now attributable to upstream data quality/liquidity rather than contract-drop at Arrow boundary.

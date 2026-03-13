# Project State

## Snapshot
- DateTime (ET): 2026-03-12 14:19:28 -04:00
- Branch: `master`
- Last Commit: `bc51cc7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: Re-verify current L0 LongPort option field alignment from actual code/tests and update `docs/LONGPORT_OPTION_FIELD_DICTIONARY.md`.
- Scope In:
  - `docs/LONGPORT_OPTION_FIELD_DICTIONARY.md`
  - `l0_ingest/feeds/longport_option_contracts.py`
  - `l0_ingest/feeds/quote_runtime.py`
  - `l0_ingest/l0_rust/src/lib.rs`
  - `l0_ingest/feeds/sanitization.py`
  - `l0_ingest/feeds/iv_baseline_sync.py`
  - `l0_ingest/feeds/tier2_poller.py`
  - `l0_ingest/feeds/tier3_poller.py`
  - `l0_ingest/tests/test_quote_runtime.py`
  - `l0_ingest/tests/test_longport_option_contracts.py`
- Scope Out:
  - Runtime behavior changes
  - L1/L2/L3/L4 implementation changes
  - OpenSpec proposal changes

## What Changed (Latest Session)
- Files:
  - `docs/LONGPORT_OPTION_FIELD_DICTIONARY.md`
- Behavior:
  - Rewrote the field dictionary from current L0 code, replacing stale “field dropped” claims with verified status buckets:
    - preserved in L0 contract
    - actively consumed in L0 downstream
    - preserved mainly for contract fidelity
  - Document now reflects that `option_quote.option_extend` and `optionchain-date-strike.standard` are already aligned in L0.
  - Document now reflects that `calc_indexes()` preserves richer official fields including `last_done/change_val/change_rate/turnover/expiry_date/strike_price/premium`.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_quote_runtime.py l0_ingest/tests/test_longport_option_contracts.py`

## Risks / Constraints
- Risk 1: The dictionary now matches verified L0 contract state, but some preserved fields are still not materially consumed downstream.
- Risk 2: Workspace contains unrelated in-progress changes; this session intentionally updated only the field dictionary and session artifacts.

## Next Action
- Immediate Next Step: Run strict session validation and hand off the updated field dictionary as the current L0 reference.
- Owner: Codex

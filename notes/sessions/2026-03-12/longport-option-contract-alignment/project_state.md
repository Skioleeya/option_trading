# Project State

## Snapshot
- DateTime (ET): 2026-03-12 13:46:12 -04:00
- Branch: `master`
- Last Commit: `bc51cc7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: Align LongPort option REST contracts at L0 only with additive raw+normalized fields.
- Scope In: `l0_ingest` runtime contracts, Rust REST row serializers, L0 IV consumers, L0 tests, `docs/SOP/L0_DATA_FEED.md`.
- Scope Out: `fetch_chain()` contract, SHM schema, `CleanQuoteEvent` schema, and all L1/L2/L3/L4 business logic.

## What Changed (Latest Session)
- Files:
  - `l0_ingest/feeds/longport_option_contracts.py`
  - `l0_ingest/feeds/quote_runtime.py`
  - `l0_ingest/feeds/sanitization.py`
  - `l0_ingest/feeds/iv_baseline_sync.py`
  - `l0_ingest/feeds/tier2_poller.py`
  - `l0_ingest/feeds/tier3_poller.py`
  - `l0_ingest/l0_rust/src/lib.rs`
  - `l0_ingest/tests/test_quote_runtime.py`
  - `l0_ingest/tests/test_longport_option_contracts.py`
  - `docs/SOP/L0_DATA_FEED.md`
- Behavior:
  - `RustQuoteRuntime` and `PythonQuoteRuntime` now return the same L0 option contracts for `option_quote`, `option_chain_info_by_date`, and `calc_indexes`.
  - Option quote rows now preserve official fields plus synthesized `option_extend` nested shape and raw+normalized aliases.
  - L0 IV consumers now prefer `implied_volatility_decimal` instead of re-guessing units independently.
- Verification:
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests/test_quote_runtime.py l0_ingest/tests/test_longport_option_contracts.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/test/run_pytest.ps1 l0_ingest/tests`
  - `cargo test` in `l0_ingest/l0_rust`

## Risks / Constraints
- Risk 1: The Python extension currently ships from the repo's existing build path; Rust source changes are compile-verified but not packaged in this session.
- Risk 2: Legacy downstream code still reads compatibility aliases; new preserved fields are intentionally not propagated beyond L0.

## Next Action
- Immediate Next Step: Run strict session validation, fix any session bookkeeping gaps, and re-run until green.
- Owner: Codex

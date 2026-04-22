# Open Tasks

## Priority Queue
- [ ] P1: subwave-f full-session dual-run capture (2026-04-02)
  - Owner: migration owner (`impl-20260402-l0-runtime-rust-cutover`)
  - Definition of Done: one full market-session Sub-wave F dual-run compare evidence recorded in handoff with required dimensions and no divergence.
  - Blocking: full-session evidence window not yet captured (current state is sample-level + probe-level evidence only).
- [ ] P2: pytest cache acl repair for l0-runtime suite (2026-04-02)
  - Owner: infra/tooling owner
  - Definition of Done: `scripts/test/run_pytest.ps1 tests/l0_runtime/` can run without `tmp/pytest_cache` ACL ownership failure.
  - Blocking: local environment ACL mismatch (`CodexSandboxOffline`) on `tmp/pytest_cache`.

## Parking Lot
- [ ] Add dedicated dual-run compare script for Sub-wave F (session-length capture + dimension summary + divergence report).
- [ ] Add health endpoint field for subscription desired/applied set to satisfy dual-run compare dimensions directly.

## Supersede Marker Rule
- Use `SUPERSEDED-BY: <session-id>` (or legacy `SUPSERSEDED-BY`) in unchecked historical items that are already resolved later.

## Completed (Recent)
- [x] Closed Sub-wave F runtime blockers by Rust owner root-fix (`FlowEngineG` keyword `date_str` call + native loader path migration for header/research services), rebuilt `shared_rust/services.pyd`, and recovered enriched payload in `python scripts/test/test_l0_l4_pipeline.py` (2026-04-02 14:42 ET)
- [x] Real-host Sub-wave F evidence sample captured (`start_backend`, SPY.US MVP, L0-L4 probe, persistence snapshot, runtime error traces) (2026-04-02 14:18 ET)

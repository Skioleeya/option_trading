# Open Tasks (Index)

## Active Session Tasks
- Path: notes/sessions/2026-03-26/active-options-partial-fallback-runtime-repair/open_tasks.md

## Global Backlog (Cross-Session)
- [ ] P1: Verify regular-hours live `atm` payload continuity with the new `[L3-PAYLOAD]` marker so `call_pct/put_pct/straddle_pct` are observed in-session, not just via history hydrate. (Owner: Codex, DUE: 2026-03-27, session: `2026-03-25/trace-depth-profile-and-tradingview-live-path-20260325`).
- [ ] P1: Verify raw-vanna card cadence during regular-hours source activity and compare metric-refresh density against the observed after-hours heartbeat baseline. (Owner: Codex, DUE: 2026-03-27, session: `2026-03-25/capture-dashboard-delta-and-surface-raw-vanna-20260325`).
- [x] P1: Switch `shared/services/l0_runtime` live consumer path from legacy SHM/event bridge to `shared/system/ipc_reader.py` on the Arrow IPC named-event contract, then add roundtrip verification. (Owner: Codex, DUE: 2026-03-27, session: `2026-03-25/rewrite-l0-in-rust-implementation-20260325`). COMPLETED-IN: `2026-03-25/cutover-arrow-consumer-and-retire-legacy-dual-write-20260325`
- [x] P1: Retire Rust legacy SHM compatibility dual-write after the Arrow IPC consumer path is live and validation stays green. (Owner: Codex, DUE: 2026-03-27, session: `2026-03-25/rewrite-l0-in-rust-implementation-20260325`). COMPLETED-IN: `2026-03-25/cutover-arrow-consumer-and-retire-legacy-dual-write-20260325`
- [x] P1: Add explicit deprecation markers for `shared/system/rust_shm_bridge.py` and the legacy rust event bridge now that `rust_only` no longer depends on them. (Owner: Codex, DUE: 2026-03-27, session: `2026-03-25/cutover-arrow-consumer-and-retire-legacy-dual-write-20260325`). COMPLETED-IN: `2026-03-25/deprecate-legacy-bridges-and-add-arrow-roundtrip-20260325`
- [x] P1: Add `tests/l0_runtime/test_arrow_roundtrip.py` to validate Rust producer -> Python Arrow reader batch roundtrip. (Owner: Codex, DUE: 2026-03-27, session: `2026-03-25/cutover-arrow-consumer-and-retire-legacy-dual-write-20260325`). COMPLETED-IN: `2026-03-25/deprecate-legacy-bridges-and-add-arrow-roundtrip-20260325`
- [ ] P1: Use the new capture-stall diagnostics to verify why the first valid post-lock ATM decay point still has not entered history/API after the 2026-03-25 startup relock fix. (Owner: Codex, DUE: 2026-03-26, session: `2026-03-25/atm-decay-capture-stall-diagnostics-20260325`).
- [x] P0: Run strict validation for `2026-03-25/atm-decay-live-continuity-repair-20260325` and sync final handoff/context evidence. (Owner: Codex, DUE: 2026-03-25, session: `2026-03-25/atm-decay-live-continuity-repair-20260325`).
- [x] P0: Repair ATM live payload continuity so `dashboard_update/dashboard_delta` keep advancing `atm.timestamp` during market hours. (Owner: Codex, DUE: 2026-03-25, session: `2026-03-25/tradingview-live-sampling-trace-20260325`). SUPERSEDED-BY: `2026-03-25/atm-decay-live-continuity-repair-20260325`
- [x] P0: Repair ATM decay history timestamp/order corruption; current persisted series contains `15:01-15:02 ET` rows ahead of current `09:5x ET` samples and can force chart `setData` backfills. (Owner: Codex, DUE: 2026-03-25, session: `2026-03-25/tradingview-live-sampling-trace-20260325`). SUPERSEDED-BY: `2026-03-25/atm-decay-live-continuity-repair-20260325`
- [ ] P1: Validate `snapshot_version_iv_probe` on a genuinely fast-cadence `ws` ATM IV path before broadening source suppression beyond `rest`. (Owner: Codex, DUE: 2026-03-27, session: `2026-03-25/snapshot-iv-drift-behavior-fix-20260325`).
- [ ] P1: Investigate implausible WS `current_volume` values dropped during the 2026-03-24 L0 after-hours penetration run and confirm whether the fault is upstream payload quality or local decode/layout mismatch. (Owner: Codex, DUE: 2026-03-26, session: `2026-03-24/l0-live-penetration-test-20s`).
- [ ] P1: 鏉╀胶些閸撯晙缍?`l4_ui` 闂堢偛褰告笟褎绁寸拠鏇炲煂 Vitest globals API 閹存牜绮烘稉鈧?compat shim閿涘本浠径宥呭弿闁?`npm --prefix l4_ui run test` 缂佽儻澹?(Owner: Codex, DUE: 2026-03-19, session: `2026-03-13/l4-ui-asian-color-semantics-audit-fix`).
- [ ] P1: Configure GitHub branch protection required check `validate-session` (Owner: Repo Admin, DUE: 2026-03-19, session: `2026-03-13/anti-garbage-code-gate-hardening`).
- [ ] P2: 閺€璺哄經楠炶泛缍婂?`refactor-governance-20260317-l0-l2-data-path-remediation-chain` 閸欏﹤鍙鹃崜鈺€缍戠€涙劖褰佸?(Owner: Codex, DUE: 2026-03-21, session: `2026-03-17/apply-fix-20260317-p2-gpu-temp-noise-and-archive`).
- [ ] P2: L0-L2 dechaos Stage-2 绾剟妲囬崐鍏兼暪閸欙綇绱橝gentG/IVBaselineSync閿?Owner: Codex, DUE: 2026-03-19, session: `2026-03-17/apply-refactor-governance-20260317-l0-l2-dechaos-chain-p1-implementation`).
- [ ] P1-CARRY: Online active-options volume verification pending (env process launch limitation). Owner: User. DUE: 2026-03-20. Session: active-options-volume-sanitize-20260319. SUPERSEDES: debt from prior session.
- [ ] P1: Verify live ATM anchor diagnostics after restart when quote connectivity is healthy. Owner: Codex. DUE: 2026-03-25. Session: 2026-03-24/fix-oi-rest-path-depth-zero-20260324.
- [ ] P1: Verify bounded `option_quote()` price repair for ATM anchor/mandatory symbols after healthy restart. Owner: Codex. DUE: 2026-03-25. Session: 2026-03-24/fix-oi-rest-path-depth-zero-20260324.
- [ ] P1: Verify a fresh ATM lock no longer persists a flat opening `0/0/0` point after the opening-tick suppression patch. Owner: Codex. DUE: 2026-03-25. Session: 2026-03-24/fix-oi-rest-path-depth-zero-20260324.
- [ ] P1: Verify persisted flat-zero ATM anchors no longer restore into active payload after restart. Owner: Codex. DUE: 2026-03-25. Session: 2026-03-24/fix-oi-rest-path-depth-zero-20260324.
- [ ] P1: Trace why first post-lock ATM decay sample still does not materialize after same-day startup lock even with startup one-shot repair, immediate subscription refresh, and unconditional recompute. Owner: Codex. DUE: 2026-03-25. Session: 2026-03-24/fix-oi-rest-path-depth-zero-20260324. SUPERSEDED-BY: `2026-03-25/atm-decay-anchor-recapture-repair-20260325`
- [ ] P1: Verify frontend ATM chart progression after the timestamp-preserving store fix. Owner: Codex. DUE: 2026-03-25. Session: `2026-03-24/fix-oi-rest-path-depth-zero-20260324`. SUPERSEDED-BY: `2026-03-25/tradingview-live-sampling-trace-20260325`

## Process
- Task details and completion evidence belong in the session-local open_tasks.md.
- Keep this file as the long-horizon queue and session pointer only.

# L0 Runtime Owner API Prerequisite Matrix (2026-04-02 ET)

## Required Owner APIs

| API | Current owner surface | Current key consumers | Target owner surface (prereq contract) | Status |
|---|---|---|---|---|
| `OptionChainBuilder` | `shared.services.l0_runtime` (Python facade owner) | `app/container.py`, `tests/l0_runtime/*` | Rust-backed typed owner surface (`shared_rust.services` or `l0_rust` stable export + neutral facade) | MISSING |
| `L0QuoteRuntime` / `RustQuoteRuntime` | `shared.services.l0_runtime.source.runtime.quote_runtime` (Python owner) | subscription/poller/sync/service modules + tests | Rust owner class export with parity constructor/diagnostics methods | MISSING |
| `APIRateLimiter` | `shared.services.l0_runtime.source.runtime.rate_limiter` (Python owner) | subscription/poller/sync/source modules + tests | Rust owner class export with same limiter semantics | MISSING |
| `FeedOrchestrator` | `shared.services.l0_runtime.services.orchestration.orchestrator` (Python owner) | runtime services + tests | Rust owner class export (or stable neutral surface backed by Rust owner) | MISSING |
| `OptionSubscriptionManager` | `shared.services.l0_runtime.services.subscription.manager` (Python owner) | orchestrator/runtime services + tests | Rust owner class export with same public manager API | MISSING |
| `IVBaselineSync` | `shared.services.l0_runtime.services.sync.iv_baseline_sync` (Python owner) | orchestrator/runtime services + `l1_compute/analysis/greeks_engine.py` | Rust owner class export with same public sync lifecycle API | MISSING |
| `build_runtime_bundle` | `shared.services.l0_runtime.source` (Python owner) | `facade.py` + runtime tests | Rust-backed runtime bundle factory at stable import surface | MISSING |
| `CallbackHooks` | `shared_rust.contracts` (Rust owner) | `facade.py` | `shared_rust.contracts` | DONE (2026-04-02) |
| `SnapshotRequest` | `shared_rust.contracts` (Rust owner) | `facade.py` | `shared_rust.contracts` | DONE (2026-04-02) |

## Retarget Order (Enforced)

1. `source/runtime` owner APIs (`L0QuoteRuntime` + `APIRateLimiter` + runtime bundle factory)
2. `services/*` owner APIs (`OptionSubscriptionManager` / `IVBaselineSync` / `FeedOrchestrator`)
3. top-level facade contracts and facade owner (`CallbackHooks` / `SnapshotRequest` / `OptionChainBuilder`)
4. delete corresponding Python owners only after per-wave parity gate passes

## Sub-wave Parity Gates

- B: sanitization parser parity on quote/depth normalization and edge-case handling.
- C: market/event bridge parity for event typing and trade/depth payload shaping.
- D: state/projection parity for version monotonicity and snapshot payload compose.
- E: service lifecycle parity for orchestration cadence, subscription flow, and sync behavior.
- F: source/runtime parity with dual-run evidence and no divergence on connectivity/profile failover.

## Dual-Run Evidence Structure (Sub-wave F)

- run length: one full market session
- required compare dimensions:
  - endpoint profile selection/failover behavior
  - subscription apply set (`desired` vs `applied`)
  - snapshot continuity (`version`, `as_of_utc`, `rust_active`, `shm_stats`)
  - operational diagnostics continuity
- divergence rule:
  - any structural contract mismatch or behavior drift above agreed threshold blocks closure

## Rollback Triggers

- required owner API missing or semantically incompatible
- consumer retarget incomplete while deletion attempted
- parity gate failure in any sub-wave
- dual-run divergence in source/runtime transition

## Hard Block Rule

If required owner APIs are not available, Python owner deletion in `impl-20260402-l0-runtime-rust-cutover`
MUST NOT proceed.

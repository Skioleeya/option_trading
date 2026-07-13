## Implementation
- [x] Add Rust-backed subscription selector for initial and dynamic phases.
- [x] Pass live chain snapshot and first-source timing from L0 orchestration.
- [x] Preserve `SPY.US`, mandatory symbols, and sentinel candidates through cap trim.
- [x] Add configuration defaults and diagnostics for phase/ranges/rebalance reason.
- [x] Remediate review findings: deterministic `wave11` native owner, stop/resubscribe state reset, and true strike-step hysteresis.
- [x] Add deterministic dynamic side guards and protection-tier cap trimming without adaptive thresholds.

## Verification
- [x] Add native selector and subscription manager tests.
- [x] Add orchestrator regression coverage for new refresh signature.
- [x] Update L0 SOP.
- [x] Verify side-level phase diagnostics and near-spot sentinel cap priority.

## ADDED Requirements

### Requirement: Owner-API Prerequisite Must Exist Before L0 Runtime Python Owner Retirement
Before any Sub-wave A-G deletion in `impl-20260402-l0-runtime-rust-cutover`, the Rust side SHALL
provide owner APIs for runtime/service classes currently required by consumers.

#### Scenario: Deletion Attempt Without Owner APIs
- **WHEN** a sub-wave attempts to delete Python owner files while required owner APIs are not exported from Rust surfaces
- **THEN** the sub-wave MUST be blocked and the deletion MUST NOT be considered complete.

### Requirement: Required Owner-API Set Must Be Explicit and Auditable
The prerequisite owner-API set SHALL include at least:
`OptionChainBuilder`, `L0QuoteRuntime` or `RustQuoteRuntime`, `APIRateLimiter`,
`FeedOrchestrator`, `OptionSubscriptionManager`, `IVBaselineSync`, `build_runtime_bundle`,
`CallbackHooks`, and `SnapshotRequest`.

#### Scenario: Incomplete Owner-API Inventory
- **WHEN** downstream cutover evidence omits any required owner API from the prerequisite set
- **THEN** prerequisite closure MUST fail.

### Requirement: Consumer Retarget Must Precede Python Owner Deletion
Consumers SHALL retarget to the approved Rust owner APIs before deleting corresponding Python owners.

#### Scenario: Python Owner Deleted Before Consumer Retarget
- **WHEN** a Python owner module is removed before all direct consumers are retargeted
- **THEN** cutover verification MUST fail and the deletion MUST be rolled back.

### Requirement: Source Runtime Closure Must Include Dual-Run Evidence
Source/runtime owner transition SHALL include one full market-session dual-run compare evidence
before sub-wave F can close.

#### Scenario: Sub-wave F Without Dual-Run Evidence
- **WHEN** sub-wave F claims completion without full-session dual-run evidence in handoff
- **THEN** closure MUST be blocked.

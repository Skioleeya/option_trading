# Magic-Number Child Constants/Config Evidence

## Objective

This artifact records the constants/config governance package for the Rust migration. It converts the root design document and the upstream dependency artifact into a concrete owner model that downstream implementation planning can consume.

## Upstream Inputs Consumed

- `02_RUST_CONSTANTS_CONFIGURATION_DESIGN.md`
- `openspec/changes/refactor-dependency-20260401-rust-contract-freeze-single-source/artifacts/contract-freeze-evidence.md`

## In Scope

- owner model for `constants` and `config`
- taxonomy for protocol, diagnostics, market microstructure, and runtime constants
- config namespace model
- anti-hardcoding controls
- validation pipeline
- downstream checklist for the `bloat` child

## Out of Scope

- runtime implementation changes
- direct module decomposition of `shared + L0`
- contract schema ownership changes
- L1/L2/L3/app implementation rewrites

## Owner Model

### Constants Owner Files

Recommended crate and files:

- `crates/constants/src/protocol.rs`
  - payload keys
  - schema version identifiers
  - IPC signal names
  - event type names
- `crates/constants/src/diagnostics.rs`
  - degraded status labels
  - health-state names
  - structured marker names
- `crates/constants/src/market_microstructure.rs`
  - row-quality labels
  - fallback-reason identifiers
  - semantic category labels shared across runtime and assembly
- `crates/constants/src/runtime.rs`
  - immutable runtime semantic labels
  - reserved internal identifiers that are not ops-tunable
- `crates/constants/src/identifiers.rs`
  - cross-domain stable identifiers that are contract-visible and reused broadly

### Config Owner Files

Recommended crate and files:

- `crates/config/src/defaults.rs`
  - compiled defaults
- `crates/config/src/env.rs`
  - environment input collection only
- `crates/config/src/validation.rs`
  - parsed-value validation and range guards
- `crates/config/src/loader.rs`
  - authority-order assembly and final resolved config
- optional layer/domain modules:
  - `crates/config/src/l0.rs`
  - `crates/config/src/active_options.rs`
  - `crates/config/src/diagnostics.rs`

### Consumption Boundary

- runtime crates may read resolved config values and constant identifiers
- runtime crates may not define their own copies of:
  - degraded status strings
  - payload keys
  - contract-visible fallback reasons
  - environment variable names
- presenter/assembler layers may consume constants only through the owner crate
- no business logic may access `os.environ` or equivalent directly after cutover

## Classification Rules

Use this rule set:

- If changing a value changes contract meaning, semantic identity, or external interpretation, it is a `constant`.
- If changing a value changes tuning policy, cadence, retry behavior, capacity, or deployment behavior without changing contract meaning, it is `config`.
- If a value looks like a threshold but is actually a stable semantic category boundary with cross-layer meaning, it must be justified explicitly before staying in `constants`.

## Classification Examples From Current Repository

### Constants

- `L0_IPC_SIGNAL_NAME`
  - reason: stable IPC contract identifier
- `UNINITIALIZED`, `ERROR`, `DISCONNECTED`
  - reason: diagnostics contract labels
- `row_quality`
  - reason: payload key and semantic surface
- `fallback_reason`
  - reason: payload key and semantic surface
- `REAL`, `FALLBACK_SYNTHETIC`, `PLACEHOLDER`
  - reason: row-quality semantic labels
- `subthreshold_volume`, `turnover_open_interest`, `engine_empty_output`
  - reason: fallback semantic identifiers
- `heartbeat_timestamp`
  - reason: stable payload key

### Config

- connect retry count currently read via `LONGPORT_CONNECT_RETRIES`
  - reason: runtime tuning, not contract meaning
- connect retry base seconds currently read via `LONGPORT_CONNECT_RETRY_BASE_SEC`
  - reason: runtime tuning
- websocket receive timeout such as `30.0`
  - reason: runtime tuning
- active-options minimum volume override
  - reason: tuning policy
- heartbeat cadence
  - reason: runtime tuning unless made contract-visible

### Values Requiring Explicit Review

- `ACTIVE_OPTIONS_DEFAULT_LIMIT`
  - likely config if UI/runtime wants tunability
  - may remain constant only if fixed by contract and non-tunable
- `ACTIVE_OPTIONS_SWITCH_CONFIRM_TICKS`
  - likely config because it tunes anti-flicker behavior
- `ACTIVE_OPTIONS_FLOW_VOLUME_THRESHOLD_MILLION`
  - constant if only formatting scale label
  - config if it controls runtime decision behavior

## Current Repository Findings

### Existing Positive Signal

- `shared/services/active_options/constants.py` already centralizes part of the Active Options literal surface
- `shared/config/*` already exists as a natural future config boundary

### Current Governance Gaps

- `shared/services/l0_runtime/source/runtime/market_data_gateway.py`
  - reads environment variables directly for retry behavior
- `shared/services/l0_runtime/source/runtime/quote_runtime.py`
  - reads `L0_IPC_SIGNAL_NAME` directly from environment as runtime source-of-truth
- `app/loops/housekeeping_loop.py`
  - defines local semantic/degraded values such as `NEUTRAL`, `missing_input`, `0.0`
- `app/loops/compute_loop.py`
  - defines local `NEUTRAL` fallback label
- payload and diagnostics labels are spread across `shared`, `app`, and `l3_assembly`

## Anti-Hardcoding Invariants

- no direct environment reads in business/runtime logic after cutover
- no payload key literals owned by presenters, assemblers, or loops
- no degraded-status label duplication across layers
- no fallback-reason duplication across runtime and assembly
- no row-quality semantic labels outside constants owner files
- no retry/timeouts hidden in implementation code

## Validation Pipeline

### 1. Magic-Number Scan

Detect:

- naked numeric thresholds in runtime modules
- unnamed retry/timeouts/cadence values
- duplicated scale constants

### 2. Duplicate-Key Scan

Detect:

- duplicated payload keys such as `row_quality`, `fallback_reason`, `heartbeat_timestamp`
- duplicated diagnostics labels

### 3. Config-Access Scan

Detect:

- direct `os.environ` or equivalent access in runtime/business modules
- environment reads outside `config` owner boundary

### 4. Owner-File Scan

Detect:

- monolithic catch-all constants file growth
- constants/config ownership overlap

### 5. Contract-Reference Scan

Detect:

- values classified against upstream dependency artifact inconsistently
- payload keys or labels redefined outside owner crates

## Authority Order

Resolved config authority order:

1. compiled defaults
2. environment-specific file
3. environment variables
4. validated runtime override, if explicitly governed

Constant authority order:

1. owner file in `constants`
2. transition mirror for Python compatibility only

No other source may define contract-visible identifiers.

## Downstream Checklist for the Bloat Child

The `bloat` child must assume:

- constants and config remain separate owner domains
- no first-wave migration slice may create new local copies of upstream semantic identifiers
- first-wave modules must identify whether each literal is:
  - consumed from constants
  - consumed from resolved config
  - pending classification blocker
- any module with direct environment reads must be wrapped behind future config ownership during implementation planning

## Literal-Extraction Sequence

1. extract contract-visible keys and semantic labels to `constants`
2. extract diagnostics labels to `constants/diagnostics`
3. extract runtime tuning values to `config`
4. replace direct env reads with config loader access
5. remove duplicate local identifiers from loops/presenters/runtime modules

## Review Conclusion

- The child now has a concrete constants/config governance artifact.
- Upstream dependency identifiers have been consumed and classified.
- Downstream `bloat` planning can use this artifact as its anti-hardcoding checklist.
- This child remains open until downstream use and final closure evidence are complete.

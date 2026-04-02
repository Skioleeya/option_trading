# Rust Migration Detailed Document 02 - Constants and Configuration Design

## 1. Objective
This document defines the mandatory constants and configuration governance model for the Rust migration. The goal is to remove hardcoding, establish authoritative ownership, and separate immutable contract semantics from tunable runtime parameters.

## 2. Governing Principle
A pure Rust migration without constants governance is not a migration. It is only a language rewrite of existing entropy.

Mandatory principles:
- no hardcoded thresholds in runtime modules
- no duplicated payload field names across layers
- no unowned magic strings
- no hidden retry or timeout values in implementation code
- every constant has one authoritative owner
- every tunable parameter is classified as configuration, not constant

## 3. Distinguish Constant from Configuration

### 3.1 Constant
A constant is immutable within a given contract or algorithm definition.
Examples:
- protocol keys
- enum-discriminant strings
- diagnostic channel names
- schema version markers
- mathematically fixed guard values tied to a contract

### 3.2 Configuration
A configuration value is intended to vary by environment, deployment, or operations policy.
Examples:
- retry interval
- timeout
- queue size
- active-options minimum volume override
- heartbeat cadence

Decision rule:
- if changing the value changes the contract, it is a constant
- if changing the value changes runtime tuning but not schema meaning, it is configuration

## 4. Recommended Crate Layout
Create a dedicated constants crate and a dedicated config crate.

Recommended structure:
```text
crates/
  constants/
    src/
      lib.rs
      protocol.rs
      diagnostics.rs
      market_microstructure.rs
      runtime.rs
      identifiers.rs
  config/
    src/
      lib.rs
      loader.rs
      defaults.rs
      env.rs
      validation.rs
```

Ownership rules:
- `constants` must not depend on runtime implementation crates
- `config` may depend on `constants` for keys and validation envelopes
- runtime crates depend on both `constants` and `config`

## 5. Constants Taxonomy

### 5.1 Protocol Constants
Owner file candidates:
- `constants/src/protocol.rs`
- `constants/src/identifiers.rs`

Examples:
- payload keys
- schema versions
- event type names
- IPC channel names
- diagnostics section keys

Requirements:
- stable naming
- explicit comments on cross-layer impact
- synchronized Python compatibility access during transition

### 5.2 Diagnostics Constants
Owner file candidate:
- `constants/src/diagnostics.rs`

Examples:
- structured log markers
- health state labels
- degraded-mode reasons
- metric names
- stall-state labels

Requirements:
- centralize all diagnostic strings
- do not let assemblers, presenters, and runtime stores invent their own labels

### 5.3 Market Microstructure Constants
Owner file candidate:
- `constants/src/market_microstructure.rs`

Examples:
- active-options fallback reason identifiers
- anti-flicker labels
- source consistency guard identifiers
- row-quality labels
- fixed semantic categories used across runtime and assembly

Requirements:
- semantic labels belong here
- tunable threshold values do not belong here unless they are contract-fixed

### 5.4 Runtime Constants
Owner file candidate:
- `constants/src/runtime.rs`

Examples:
- default non-overridable capacity limits
- static backpressure labels
- reserved internal IDs

Requirements:
- use only for immutable runtime semantics
- if ops should tune it, move it to `config`

## 6. Configuration Model

### 6.1 Recommended Config Namespaces
```text
config.runtime.*
config.l0.*
config.l1.*
config.l2.*
config.l3.*
config.active_options.*
config.diagnostics.*
```

### 6.2 Config File Strategy
Recommended sources, ordered by authority:
1. compiled defaults in `config/defaults.rs`
2. environment-specific file
3. environment variables
4. validated runtime override, if governance permits it

Rules:
- never read ad hoc environment variables directly inside business logic
- all environment access goes through `config`
- all parsed values must be validated before runtime use

### 6.3 Example Classification
- `ACTIVE_OPTIONS_FALLBACK_REASON_SUBTHRESHOLD_VOLUME`
  - constant
- `active_options.min_volume`
  - config
- `DIAGNOSTIC_STATUS_STALLED`
  - constant
- `l0.quote_connect_timeout_ms`
  - config
- `PAYLOAD_KEY_RUST_ACTIVE`
  - constant

## 7. Anti-Hardcoding Enforcement Rules
Every migrated runtime module must pass these checks:
- no naked numeric thresholds in algorithm code
- no duplicated string keys for payload fields
- no inline retry schedules
- no inline log marker labels
- no duplicated degraded-mode reason strings

Mandatory review questions:
- does this literal encode contract meaning
- does this literal encode tuning policy
- does this literal already exist in a constants owner file
- should this be promoted from code to config

## 8. Engineering Cohesion and Coupling Rules
This governance model is only acceptable if it preserves high cohesion and low coupling.

Mandatory structural rules:
- `constants` only owns immutable semantic identifiers and contract-level fixed values
- `config` only owns tunable runtime parameters and validated loading logic
- runtime crates consume `constants` and `config`, but do not redefine either
- no business module may read environment variables directly
- no presenter or assembler may define protocol keys locally

Coupling controls:
- constants are grouped by domain ownership, not by convenience
- configuration namespaces follow layer and domain boundaries
- no monolithic catch-all owner file is allowed

## 9. Suggested Validation Pipeline
Before accepting any migrated Rust module:
- run magic-number scan
- run duplicate-key scan
- run config-access scan
- run owner-file scan
- run contract-reference scan

Recommended acceptance criteria:
- zero duplicated contract keys in changed scope
- zero new magic-number violations in runtime files
- zero direct environment reads in runtime modules

## 10. Migration Application Strategy
Apply constants governance in this sequence:
1. inventory existing literals in `shared + L0`
2. classify each literal as constant or config
3. create owner files in `constants` and `config`
4. replace direct literals in Rust target modules
5. add compatibility access for Python transition paths
6. block any new literal drift by review gate

## 11. Risks and Controls
Risk:
- turning every value into config, including values that define protocol meaning
Control:
- keep contract-defining values in `constants`

Risk:
- leaving old Python defaults in place while Rust introduces new defaults
Control:
- Rust becomes source of truth; Python only reads mirrored values

Risk:
- creating a monolithic constants file
Control:
- split by domain ownership, not by language or by convenience

## 12. Review and Revision
Initial draft issue found during self-review:
- The earlier plan did not cleanly separate semantic labels from tunable thresholds.

Revision applied:
- semantic identifiers are now required to stay in `constants`
- runtime-tunable values are required to move to `config`
- direct environment reads inside business logic are now explicitly forbidden

Normative review conclusion:
- The model is consistent.
- The ownership rules are testable.
- The classification rule is objective enough for code review.

Landing feasibility conclusion:
- This constants model is practical and should be established before any large Rust runtime cutover.



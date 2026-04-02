PARENT_CHANGE_ID: refactor-governance-20260401-rust-runtime-migration-chain
DEPENDENCY_ORDER: 3
BLOCKED_BY: refactor-magic-number-20260401-rust-constants-config-governance

## Why

The `shared + L0` planning document defines the first executable migration boundary, but that boundary is only safe after contract freeze and constants/config governance have already been fixed.

This child proposal converts the root-level module-audit document into an OpenSpec-governed modular-boundary proposal for the first implementation-oriented migration slice.

## What Changes

This child proposal defines the governed execution boundary for the first Rust migration slice:
- classify `shared + L0` modules by role, migration class, and risk
- define the first-wave migration set
- define decomposition rules for `shared/services/l0_runtime/*`
- define early Rust targets in `shared/contracts`, `shared/models`, `shared/services/active_options`, and `l0_rust`
- define verification, rollback radius, and closure criteria for the first executable boundary
- define the boundary evidence package and implementation-session entry conditions

## Scope

- `shared` and `L0` module classification
- first-wave migration set definition
- module decomposition constraints
- validation matrix and rollback radius
- downstream handoff requirements for future implementation sessions
- boundary evidence package

## Rollback

If the module boundary still mixes contract, runtime, compute, and compat responsibilities without clear ownership, this child proposal remains open and no implementation session may claim the boundary is ready.

## Evidence Sources

- Shared/L0 audit source: `01_RUST_SHARED_L0_MODULE_AUDIT.md`
- Upstream contract-freeze source: `openspec/changes/refactor-dependency-20260401-rust-contract-freeze-single-source/artifacts/contract-freeze-evidence.md`
- Upstream constants/config source: `openspec/changes/refactor-magic-number-20260401-rust-constants-config-governance/artifacts/constants-config-evidence.md`
- OpenSpec chain validation source: `scripts/policy/check_openspec_chain.py`
- Strict validation source: `scripts/validate_session.ps1 -Strict`

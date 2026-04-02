PARENT_CHANGE_ID: refactor-governance-20260401-rust-runtime-migration-chain
DEPENDENCY_ORDER: 2
BLOCKED_BY: refactor-dependency-20260401-rust-contract-freeze-single-source

## Why

Constants and configuration governance must follow contract freeze, not precede it. Without frozen semantic ownership, a constants program cannot distinguish contract-owned identifiers from runtime-tunable parameters with sufficient rigor.

This child proposal turns the root-level constants and configuration document into an OpenSpec-governed anti-hardcoding change unit.

## What Changes

This child proposal defines the constants and configuration governance boundary for the Rust migration:
- separate `constants` ownership from `config` ownership
- define taxonomy for protocol, diagnostics, microstructure, and runtime constants
- define config namespaces and validation rules
- prohibit direct environment reads in business logic
- define anti-hardcoding validation checks for migrated Rust modules
- define the constants/config evidence package and downstream governance checklist

## Scope

- constants taxonomy and owner files
- configuration namespaces and loader boundary
- no-hardcoding enforcement rules
- cohesion and coupling constraints for constants versus config
- migration application order for literal extraction
- constants/config evidence package

## Rollback

If constants ownership, config ownership, or environment-access rules remain ambiguous, this child proposal remains open and the downstream `shared + L0` boundary child cannot close.

## Evidence Sources

- Constants/config design source: `02_RUST_CONSTANTS_CONFIGURATION_DESIGN.md`
- Upstream contract-freeze source: `openspec/changes/refactor-dependency-20260401-rust-contract-freeze-single-source/artifacts/contract-freeze-evidence.md`
- OpenSpec chain validation source: `scripts/policy/check_openspec_chain.py`
- Strict validation source: `scripts/validate_session.ps1 -Strict`

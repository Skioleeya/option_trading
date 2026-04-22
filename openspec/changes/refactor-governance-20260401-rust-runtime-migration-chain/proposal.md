## Why

The repository now has a documented Rust migration direction, but it does not yet have an executable OpenSpec governance chain that enforces ordering, completeness, anti-drift controls, and closure criteria.

Without a parent proposal and ordered child proposals, three risks remain active:
1. contract freeze may be bypassed while implementation moves ahead
2. constants governance may be treated as optional and regress into hardcoding
3. `shared + L0` migration planning may proceed without a controlled dependency boundary

## What Changes

This parent proposal creates one ordered governance chain for the Rust runtime migration program:

1. `refactor-dependency-20260401-rust-contract-freeze-single-source`
2. `refactor-magic-number-20260401-rust-constants-config-governance`
3. `refactor-bloat-20260401-rust-shared-l0-migration-boundary`
4. `refactor-nesting-20260401-rust-migration-chain-reconciliation`

The parent proposal does not implement runtime behavior. It defines:
- dependency order
- completion gates
- rollback rules
- documentation completeness rules
- mandatory anti-hardcoding and anti-coupling constraints for children
- governance evidence sources for strict validation, OpenSpec chain validation, and quality thresholds

## Scope

- OpenSpec governance only
- parent-child dependency order
- closure gates and rollback policy
- proposal completeness and normative quality rules
- governance evidence source-of-truth references

## Child Proposals

- `refactor-dependency-20260401-rust-contract-freeze-single-source`
- `refactor-magic-number-20260401-rust-constants-config-governance`
- `refactor-bloat-20260401-rust-shared-l0-migration-boundary`
- `refactor-nesting-20260401-rust-migration-chain-reconciliation`

## Rollback

If any child proposal fails contract consistency review, anti-hardcoding review, cross-proposal validation, reconciliation review, or strict session validation, the governance chain halts at the latest validated child and the parent remains open.

## Governance Evidence Sources

- Strict session validation source of truth: `scripts/validate_session.ps1 -Strict`
- OpenSpec chain validation source of truth: `scripts/policy/check_openspec_chain.py`
- Quality threshold source of truth: `scripts/policy/check_quality_gates.py` and `scripts/policy/quality_thresholds.json`
- Session continuity source of truth: `notes/context/*` plus the active `notes/sessions/YYYY-MM-DD/<task-id>/` record



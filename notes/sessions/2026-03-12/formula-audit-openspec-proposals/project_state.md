# Project State

## Snapshot
- DateTime (ET): 2026-03-12 14:02:46 -04:00
- Branch: `master`
- Last Commit: `bc51cc7`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED`

## Current Focus
- Primary Goal: Convert the 2024-2026 option-formula audit findings into a parent+child OpenSpec remediation set with file-level fields, rename suggestions, and test points.
- Scope In:
  - `openspec/changes/formula-semantic-contract-parent-governance/*`
  - `openspec/changes/formula-semantic-phase-a-vrp-gex-stopgap/*`
  - `openspec/changes/formula-semantic-phase-b-skew-and-raw-exposure-contracts/*`
  - `openspec/changes/formula-semantic-phase-c-provenance-and-heuristic-labels/*`
  - `openspec/changes/formula-semantic-phase-d-research-metric-upgrades/*`
  - `notes/sessions/2026-03-12/formula-audit-openspec-proposals/*`
  - `notes/context/*`
- Scope Out:
  - L0/L1/L2/L3/L4 runtime implementation changes
  - Rust/Python contract changes beyond proposal text
  - Live deployment, packaging, or data backfill

## What Changed (Latest Session)
- Files:
  - `openspec/changes/formula-semantic-contract-parent-governance/proposal.md`
  - `openspec/changes/formula-semantic-contract-parent-governance/design.md`
  - `openspec/changes/formula-semantic-contract-parent-governance/tasks.md`
  - `openspec/changes/formula-semantic-contract-parent-governance/specs/formula-remediation-governance/spec.md`
  - `openspec/changes/formula-semantic-phase-a-vrp-gex-stopgap/proposal.md`
  - `openspec/changes/formula-semantic-phase-a-vrp-gex-stopgap/design.md`
  - `openspec/changes/formula-semantic-phase-a-vrp-gex-stopgap/tasks.md`
  - `openspec/changes/formula-semantic-phase-a-vrp-gex-stopgap/specs/metric-unit-and-proxy-semantics/spec.md`
  - `openspec/changes/formula-semantic-phase-b-skew-and-raw-exposure-contracts/proposal.md`
  - `openspec/changes/formula-semantic-phase-b-skew-and-raw-exposure-contracts/design.md`
  - `openspec/changes/formula-semantic-phase-b-skew-and-raw-exposure-contracts/tasks.md`
  - `openspec/changes/formula-semantic-phase-b-skew-and-raw-exposure-contracts/specs/skew-and-raw-greek-contracts/spec.md`
  - `openspec/changes/formula-semantic-phase-c-provenance-and-heuristic-labels/proposal.md`
  - `openspec/changes/formula-semantic-phase-c-provenance-and-heuristic-labels/design.md`
  - `openspec/changes/formula-semantic-phase-c-provenance-and-heuristic-labels/tasks.md`
  - `openspec/changes/formula-semantic-phase-c-provenance-and-heuristic-labels/specs/metric-provenance-registry/spec.md`
  - `openspec/changes/formula-semantic-phase-d-research-metric-upgrades/proposal.md`
  - `openspec/changes/formula-semantic-phase-d-research-metric-upgrades/design.md`
  - `openspec/changes/formula-semantic-phase-d-research-metric-upgrades/tasks.md`
  - `openspec/changes/formula-semantic-phase-d-research-metric-upgrades/specs/research-metric-upgrades/spec.md`
- Behavior:
  - Added one governance parent proposal and four ordered child proposals (`A -> B -> C -> D`) that translate the formula audit into executable remediation phases.
  - Each child proposal pins exact target files, fields, rename strategy, compatibility rules, and regression entry points.
  - No runtime code changed in this session; only proposal and session artifacts were added.
- Verification:
  - `openspec list`
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict`

## Risks / Constraints
- Risk 1: The proposals intentionally stop at planning/governance; runtime semantics remain unchanged until child proposals are implemented.
- Risk 2: `openspec list` emitted PostHog telemetry network errors under sandboxed network restrictions, but the local change set was still discovered successfully.

## Next Action
- Immediate Next Step: Run strict session validation, then hand off the proposal set as the implementation roadmap for P0/P1/P2 remediation.
- Owner: Codex

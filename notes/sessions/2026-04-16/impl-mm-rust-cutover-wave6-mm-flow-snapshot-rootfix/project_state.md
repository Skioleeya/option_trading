# Project State

## Snapshot
- DateTime (ET): 2026-04-16 19:22
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `e91cff0`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `DEGRADED` (awaiting post-fix live bring-up verification)

## Current Focus
- Primary Goal: fix MM-flow P1/P2 review findings at root cause without fallback/compat logic.
- Scope In: L0 Rust event/schema/state persistence, MM snapshot Rust aggregator, contract-aligned tests.
- Scope Out: unrelated L2/L3/L4 feature refactors already in working tree.

## What Changed (Latest Session)
- Files: `l0_ingest/l0_rust/*` event pipeline/state files, `shared_rust_services/src/mm_flow_snapshot.rs`, targeted pytest files.
- Behavior: chain snapshot now owns depth top-of-book side volumes and trade condition fields; MM metrics removed legacy size fallback.
- Verification: targeted pytest suite green after Rust rebuild and runtime artifact refresh.

## Risks / Constraints
- Risk 1: strict validation requires session/context files fully synchronized before handoff.
- Risk 2: live runtime validation depends on host LongPort connectivity and startup scripts.

## Next Action
- Immediate Next Step: pass strict validation, then run Redis/backend/frontend and 120s postmarket live check.
- Owner: Codex

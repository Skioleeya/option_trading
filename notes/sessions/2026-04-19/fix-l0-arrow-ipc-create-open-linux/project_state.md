# Project State

## Snapshot
- DateTime (ET): 2026-04-19 16:16
- Branch: unknown (workspace has no `.git` metadata in this environment)
- Last Commit: unknown
- Environment:
  - Market: `CLOSED` (Sunday)
  - Data Feed: `OK`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: Eliminate Linux L0 Arrow IPC startup blocker and verify weekend runtime health.
- Scope In: L0 Rust IPC writer/reader path, native artifact deployment, host startup verification.
- Scope Out: Strategy/business rule redesign in L1-L3.

## What Changed (Latest Session)
- Files:
  - `l0_ingest/l0_rust/src/ipc_legacy.rs`
  - `l0_ingest/l0_rust/src/ipc_runtime.rs`
  - `l0_ingest/l0_rust/src/windows_signal.rs`
  - `shared/services/l0_runtime/_native_generated/{l0_rust.so,wave10/l0_rust.so}`
- Behavior:
  - Linux `create_or_open` path now works; backend startup no longer stalls on Arrow writer init.
  - Host startup chain reaches stable Redis+Backend+Frontend listening state.
- Verification:
  - `python3 manage.py start-all`
  - `python3 manage.py start-all --verify-only`
  - Backend log after latest `[BOOT]` has zero `MappingIdExists` / `writer_not_ready_timeout` hits.

## Risks / Constraints
- Risk 1: Frontend dependency tree has prior instability history; watch for npm registry/network intermittency.
- Risk 2: GPU-tier warnings remain in compute path (`cupy/numba` unavailable), but non-blocking for startup.

## Next Action
- Immediate Next Step: Keep runtime under observation in next live session and capture sustained L0->L4 telemetry.
- Owner: Codex / operator

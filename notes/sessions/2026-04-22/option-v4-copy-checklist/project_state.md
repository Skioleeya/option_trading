# Project State

## Snapshot
- DateTime (ET): 2026-04-22 10:41:12 -0400
- Branch: `fix/frontend-data-zero-fallback`
- Last Commit: `9f5ad57`
- Environment:
  - Market: `OPEN`
  - Data Feed: `OK`
  - L0-L4 Pipeline: `RUNNING`

## Current Focus
- Primary Goal: produce a verified Scheme A checklist for copying the current source tree into `E:\US.market\Option_v4` without migrating the runtime off WSL2.
- Scope In:
  - current working tree and uncommitted source state
  - ignore/runtime artifact audit
  - copy-command rehearsal into a local probe directory
  - exact post-copy verification steps
- Scope Out:
  - executing the real copy to `E:\US.market\Option_v4`
  - Windows-native runtime migration
  - rebuilding native modules for Windows

## What Changed (Latest Session)
- Files:
  - `notes/sessions/2026-04-22/option-v4-copy-checklist/scheme_a_option_v4_copy_checklist.md`
- Behavior:
  - created a verified source-only copy checklist for `Option_v4`
  - confirmed the live stack can remain running for Scheme A because the copy excludes runtime-write directories
  - identified `.mypy_cache/` as an extra local-cache exclusion not currently covered by `.gitignore`
- Verification:
  - `python3 manage.py start-all --verify-only`
  - `git status --short`
  - `git ls-files -o -i --exclude-standard`
  - `rsync` probe copy to `tmp/option_v4_copy_probe_v2/`
  - source-presence and exclusion checks against the probe copy

## Risks / Constraints
- Risk 1: `--delete` is appropriate only if `E:\US.market\Option_v4` is intended to be a true mirror and not a mixed-use folder.
- Risk 2: copying while a user/editor is still saving source files can produce a non-deterministic snapshot even though runtime artifacts are excluded.

## Next Action
- Immediate Next Step: hand the verified Scheme A checklist to the user for approval before executing any real copy into `E:\US.market\Option_v4`.
- Owner: Codex

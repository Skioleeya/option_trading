# Project State

## Snapshot
- DateTime (ET): 2026-04-02 08:17:22 -04:00
- Branch: `chore/sync-all-local-changes-20260313`
- Last Commit: `7fb0f53`
- Environment:
  - Market: `CLOSED`
  - Data Feed: `DEGRADED`
  - L0-L4 Pipeline: `OK`

## Current Focus
- Primary Goal: move Cargo build outputs to a standard external target directory under `%USERPROFILE%\\.cargo` without polluting `.codex/memories`
- Scope In:
  - `.cargo/config.toml`
  - `.gitignore`
- Scope Out:
  - runtime source files
  - OpenSpec records
  - SOP documents

## What Changed (Latest Session)
- Files:
  - added `.cargo/config.toml`
  - updated `.gitignore`
- Behavior:
  - Cargo now uses `C:\Users\Lenovo\.cargo\option_v3_target` as the default target directory for repo builds on this machine
  - `.cargo/config.toml` is ignored locally so the machine-specific Windows path does not leak into CI or other environments
- Verification:
  - `cargo build --release --manifest-path shared_rust_services/Cargo.toml` passed using the new target-dir after elevation

## Risks / Constraints
- Risk 1: the configured path is intentionally machine-specific and will only work on this host unless another machine provides its own local `.cargo/config.toml`
- Risk 2: sandboxed builds cannot write to `%USERPROFILE%\\.cargo` without elevation, so verification needed one escalated run

## Next Action
- Immediate Next Step: keep this local-only and reuse it for the remaining Rust crate waves instead of writing build outputs into repo-local `target/` trees or `.codex/memories`
- Owner: Codex

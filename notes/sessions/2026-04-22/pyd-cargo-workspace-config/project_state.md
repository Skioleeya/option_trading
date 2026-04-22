# Project State

## Snapshot
- DateTime (ET): 2026-04-22 11:35:32 -04:00
- Branch: `unknown` (source-only mirror without `.git`)
- Last Commit: `unknown`
- Environment:
  - Market: `OPEN`
  - Data Feed: `STOPPED`
  - L0-L4 Pipeline: `STOPPED`

## Current Focus
- Primary Goal: configure `.pyd` compile path so Cargo state is enforced inside workspace, not user/global directories.
- Scope In:
  - workspace Cargo config (`.cargo/config.toml`)
  - unified CLI command for Rust `.pyd` owner build/check with workspace-local cargo dirs
  - docs/session/context sync
- Scope Out:
  - runtime strategy changes in L0-L4
  - broker-dependent live startup evidence
  - external network credential remediation

## What Changed (Latest Session)
- Files:
  - `.cargo/config.toml`
  - `.gitignore`
  - `infra/ops_cli/build_pyd.py`
  - `manage.py`
  - `scripts/README.md`
  - session/context files
- Behavior:
  - introduced `python manage.py build-pyd` entrypoint
  - command hard-sets `CARGO_HOME=tmp/cargo_home` and `CARGO_TARGET_DIR=tmp/cargo_target`
  - added workspace cargo target-dir config `[build] target-dir = "tmp/cargo_target"`
  - removed machine-local cargo config exclusion by tracking `.cargo/config.toml`
- Verification:
  - `python manage.py --help` shows `build-pyd`
  - `python manage.py build-pyd --check --stop-on-error` uses workspace env paths (printed)
  - `python manage.py check-layer-boundaries` passed
  - cargo checks blocked by crates.io SSL credential error (`SEC_E_NO_CREDENTIALS`) on host

## Risks / Constraints
- Risk 1: host TLS credential issue prevents dependency fetch from crates.io, so cargo check/build cannot complete in this environment.
- Risk 2: workspace still contains ACL-restricted temp subdirs from earlier pytest runs (`tmp/pytest_basetemp`, `tmp/win_temp`), which may affect unrelated local tooling.

## Next Action
- Immediate Next Step: fix host TLS credential chain (or pre-seed cargo cache) and rerun `python manage.py build-pyd --check --all`.
- Owner: Codex

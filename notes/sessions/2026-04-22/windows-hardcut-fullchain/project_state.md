# Project State

## Snapshot
- DateTime (ET): 2026-04-22 11:24:54 -04:00
- Branch: `unknown` (source-only mirror without `.git`)
- Last Commit: `unknown`
- Environment:
  - Market: `OPEN`
  - Data Feed: `STOPPED`
  - L0-L4 Pipeline: `STOPPED`

## Current Focus
- Primary Goal: execute Windows-only hard cut for governance contracts, ops CLI runtime, and SOP/docs with no compatibility/fallback path.
- Scope In:
  - `infra/ops_cli` hard cut (`start_backend`, `start_all`, `redis_preflight`, `validate_session`, `eod`)
  - policy gate update for OpenSpec command matcher
  - AGENTS/SOP/scripts documentation hard cut to `python manage.py` and Windows runtime contract
  - session/context sync and strict validation evidence
- Scope Out:
  - business-layer runtime feature changes in `l0`-`l4`
  - live stack startup on broker host
  - historical session rewrite

## What Changed (Latest Session)
- Files:
  - governance/docs: `AGENTS.md`, `scripts/README.md`, `docs/SOP/*`
  - ops CLI: `infra/ops_cli/start_backend.py`, `start_all.py`, `redis_preflight.py`, `eod.py`, `validate_session.py`
  - policy gate: `scripts/policy/check_openspec_chain.py`
  - tests: `infra/ops_cli/test_start_all.py`
  - CLI description: `manage.py`
- Behavior:
  - all enforced command examples switched to `python manage.py ...`
  - startup/runtime contract is Windows-only (`start-backend`, `start-all`, Redis owner preflight)
  - Linux-only process/filesystem dependencies (`pgrep/pkill/findmnt/ext4/systemd/.venv/bin`) removed from active paths
  - EOD scheduling switched to Windows Task Scheduler (`schtasks`) preview/apply flow
  - strict validation subprocess calls now use current Python executable instead of hardcoded `python3`
- Verification:
  - `python manage.py start-backend --dry-run` passed
  - `python manage.py register-eod-bucket-task --output-dir tmp/schtasks` passed
  - `python manage.py check-layer-boundaries` passed
  - targeted pytest remains blocked by host ACL issue on pytest temp directories (`WinError 5`)

## Risks / Constraints
- Risk 1: host ACL currently blocks pytest `tmp_path` fixtures (`WinError 5`), so runtime test suite evidence is constrained to non-pytest checks in this session.
- Risk 2: this workspace is a source-only mirror (no `.git`), so commit hash/branch provenance cannot be recorded beyond `unknown`.

## Next Action
- Immediate Next Step: finish strict validation and finalize handoff with debt/open-spec exemptions documented.
- Owner: Codex

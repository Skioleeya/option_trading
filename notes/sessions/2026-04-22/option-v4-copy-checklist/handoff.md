# Handoff

## Session Summary
- DateTime (ET): 2026-04-22 10:41:12 -0400
- Goal: produce a fully reviewed and verified Scheme A checklist for mirroring the current source tree into `E:\US.market\Option_v4`.
- Outcome: complete. The checklist is written, the copy command was rehearsed locally, exclusions were verified, and the live system was confirmed healthy during planning.

## What Changed
- Code / Docs Files:
  - `notes/sessions/2026-04-22/option-v4-copy-checklist/scheme_a_option_v4_copy_checklist.md`
- Runtime / Infra Changes:
  - none; this session only audited and verified the source-only copy procedure
- Commands Run:
  - `python3 manage.py new-session --task-id option-v4-copy-checklist`
  - `python3 manage.py start-all --verify-only`
  - `git status --short`
  - `git ls-files -o -i --exclude-standard`
  - `rsync -a --delete --exclude='.git/' --exclude='.mypy_cache/' --filter=':- .gitignore' ./ tmp/option_v4_copy_probe_v2/`

## Verification
- Passed:
  - `python3 manage.py start-all --verify-only` -> `Redis 6380: True`, `Backend 8001: True`, `Frontend 5173: True`
  - `git status --short` confirmed the source tree has uncommitted source changes that a Git archive would miss
  - `git ls-files -o -i --exclude-standard` identified ignored runtime/cache content and revealed `.mypy_cache/` as an extra explicit exclusion requirement
  - probe copy under `tmp/option_v4_copy_probe_v2/` preserved required source files such as `manage.py`, `infra/ops_cli/redis_preflight.py`, `shared/system/redis_service.py`, `最新的启动步骤文档.md`
  - probe copy excluded `.git/`, `.venv/`, `data/`, `logs/`, `tmp/`, `var/redis/`, `node_modules/`, `dist/`, `.mypy_cache/`, `*.so`, `*.pyd`
  - `python3 manage.py validate-session --strict` -> first run failed only because strict-validation evidence had not yet been recorded in session files; rerun required after session metadata update
- Failed / Not Run:
  - real copy to `E:\US.market\Option_v4` was intentionally not executed in this session

## Pending
- Must Do Next:
  - get explicit user approval before executing the real copy to `E:\US.market\Option_v4`
- Nice to Have:
  - if the target folder already contains unrelated files, decide whether `--delete` is acceptable or whether a non-destructive variant is preferred

## Debt Record (Mandatory)
- DEBT-EXEMPT: planning-only session; no runtime or contract behavior changed
- DEBT-OWNER: Codex
- DEBT-DUE: 2026-04-22
- DEBT-RISK: none
- OPENSPEC-EXEMPT: documentation/procedure session only
- DEBT-NEW: 0
- DEBT-CLOSED: 0
- DEBT-DELTA: 0
- DEBT-JUSTIFICATION:
- RUNTIME-ARTIFACT-EXEMPT: local probe copies under `tmp/option_v4_copy_probe*` were created only to verify the command and are gitignored

## How To Continue
- Start Command: none; this session prepared a checklist, it did not change runtime state
- Key Logs: none
- First File To Read: `notes/sessions/2026-04-22/option-v4-copy-checklist/scheme_a_option_v4_copy_checklist.md`

# Scheme A — `Option_v4` Source-Only Copy Checklist

## Goal

Create a clean source snapshot of the current working tree at `E:\US.market\Option_v4` without treating the Windows copy as the live runtime and without copying runtime/cache/generated artifacts.

## Evidence Basis

- Current live stack is up via `python3 manage.py start-all --verify-only`:
  - `Redis 6380: True`
  - `Backend 8001: True`
  - `Frontend 5173: True`
- Current working tree contains uncommitted source changes:
  - `git status --short` shows modified tracked files plus untracked source/session files.
- Runtime artifacts are explicitly non-source:
  - `.gitignore` excludes `data/`, `logs/`, `tmp/`, `var/redis/`, `.venv/`, `*.so`, `*.pyd`, `*.aof`, `*.rdb`
- Native Linux artifacts exist and must not be copied into a Windows code mirror:
  - `shared_rust/contracts.so`
  - `shared_rust/models.so`
  - `shared_rust/services.so`
  - `shared_rust/services_l0_support.so`
- Dry-run copy rehearsal was validated in-repo:
  - `rsync -a --delete --exclude='.git/' --exclude='.mypy_cache/' --filter=':- .gitignore' ./ tmp/option_v4_copy_probe_v2/`
  - Result kept current source files, including uncommitted files, and excluded `.git/`, `.venv/`, `data/`, `logs/`, `tmp/`, `var/redis/`, `node_modules/`, `dist/`, `.mypy_cache/`, `*.so`, `*.pyd`

## Hard Rules

1. This is a source-only mirror, not a runnable Windows cutover.
2. Do not use `E:\US.market\Option_v4` as the current live runtime owner.
3. Do not copy `.git/`, runtime data, caches, logs, Linux native modules, or virtualenv contents.
4. Do not edit source files during the copy window.

## Pre-Copy Checklist

1. Confirm the live stack is healthy, but do not stop it just for Scheme A:
   ```bash
   python3 manage.py start-all --verify-only
   ```
2. Confirm the current source state you intend to mirror:
   ```bash
   git status --short
   ```
3. Ensure the target parent exists on Windows:
   - `E:\US.market\`
4. Ensure no editor/refactor/save-all job is actively mutating source files during the copy.

## Verified Copy Command

Run from the repo root in WSL:

```bash
mkdir -p /mnt/e/US.market/Option_v4
rsync -a \
  --delete \
  --exclude='.git/' \
  --exclude='.mypy_cache/' \
  --filter=':- .gitignore' \
  ./ /mnt/e/US.market/Option_v4/
```

## Why This Command

- `rsync -a`: preserves the working tree layout and current file contents
- `--delete`: makes the target mirror match the selected source set exactly
- `--exclude='.git/'`: prevents repo metadata copy
- `--exclude='.mypy_cache/'`: required because current `.gitignore` does not exclude it
- `--filter=':- .gitignore'`: reuses the repo's ignore contract so runtime/cache artifacts are not copied, while still keeping untracked source files that are not ignored

## Immediate Post-Copy Checks

Run in WSL:

```bash
test -f /mnt/e/US.market/Option_v4/manage.py
test -f /mnt/e/US.market/Option_v4/infra/ops_cli/redis_preflight.py
test -f /mnt/e/US.market/Option_v4/最新的启动步骤文档.md
test ! -d /mnt/e/US.market/Option_v4/.git
test ! -d /mnt/e/US.market/Option_v4/.venv
test ! -d /mnt/e/US.market/Option_v4/logs
test ! -d /mnt/e/US.market/Option_v4/data
test ! -d /mnt/e/US.market/Option_v4/var/redis
find /mnt/e/US.market/Option_v4 -maxdepth 3 \( -name '*.so' -o -name '*.pyd' \) -print
```

Expected result:

- required source files exist
- excluded runtime directories do not exist
- native module search returns no output

## What Must Not Be Interpreted From This Copy

- It does not prove Windows-native runtime compatibility.
- It does not provide a valid Windows Python environment.
- It does not provide Windows `.pyd` builds.
- It does not replace the current WSL ext4 live environment.

## If You Later Want To Develop In Windows

That is a separate platform migration task. It requires:

1. fresh Windows venv
2. fresh Node install
3. Rust rebuild to Windows native extensions
4. startup contract review
5. full host verification on Windows

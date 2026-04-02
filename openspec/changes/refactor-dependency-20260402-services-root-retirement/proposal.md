PARENT_CHANGE_ID: refactor-governance-20260401-rust-runtime-migration-chain
DEPENDENCY_ORDER: 21-A
BLOCKED_BY: none

## Why

`shared_rust/services_root.pyd` is a transitional artifact created during Wave 16
(`wave16-shared-services-root-retirement`) as an intermediate namespace for realized-vol
and history functions. `shared_rust.services` now exports a strict superset of all symbols
previously in `services_root`. A grep scan on 2026-04-02 ET found zero live runtime
Python files importing from `shared_rust.services_root`. The artifact is dead weight that
adds namespace surface without any consumer.

## What Changes

1. **Delete** `shared_rust/services_root.pyd` from the repository.
2. **No consumer retargeting required.** Zero live import sites confirmed.
3. **No Rust source changes.** The `.pyd` file is a compiled artifact; no `.rs` source
   exists under `shared_rust/src/` for `services_root` — it was generated from
   `shared_rust_services` with an older entry-point name.

## Scope

In:
- `shared_rust/services_root.pyd` — deletion only

Out:
- `shared_rust/services.pyd` — not touched
- `shared_rust_services/src/` — no Rust source changes
- All Python consumer files — no changes required

## Hard Governance Prohibitions

- Must not touch `shared_rust/services.pyd` or any other `.pyd` file.
- Must not introduce a compatibility shim or re-export for `services_root`.
- Deletion is the only permitted action.

## Verification Gate

1. `python -c "import shared_rust.services_root"` must raise `ModuleNotFoundError`.
2. `python -c "from shared_rust.services import build_columnar_payload, RollingRealizedVolatility; print('services-ok')"` must pass.
3. `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` must pass.

## Rollback

Restore `shared_rust/services_root.pyd` from `git restore shared_rust/services_root.pyd`.
No consumer code was changed, so rollback has zero blast radius.

## Risk

LOW. Zero live consumers confirmed by scan on 2026-04-02 ET:
`rg "services_root" --include="*.py" app l0_ingest l1_compute l2_decision l3_assembly l4_ui shared scripts` → 0 matches in runtime source.

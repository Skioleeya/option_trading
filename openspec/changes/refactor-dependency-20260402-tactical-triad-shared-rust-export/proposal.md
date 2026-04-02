PARENT_CHANGE_ID: refactor-governance-20260401-rust-runtime-migration-chain
DEPENDENCY_ORDER: 21
BLOCKED_BY: none
REQUIRED_BEFORE: impl-20260402-tactical-triad-wrapper-retirement

## Why

`shared/system/tactical_triad_logic.py` is the only remaining `shared.system` file whose
Rust computation owner (`l0_ingest/l0_rust/src/tactical_triad_logic.rs`) is not yet
accessible from a cross-layer-neutral Python namespace.

Its 5 consumers are in `l2_decision/` and `l3_assembly/`. Per `CLAUDE.md` layer import
rules, L2 and L3 must not import from `shared.services.l0_runtime.*`. The Python wrapper
currently hides this violation; retiring it requires the Rust functions to be available at
`shared_rust.services`.

`shared_rust_services` compiles independently of `l0_ingest/l0_rust`. Therefore, the Rust
source in `tactical_triad_logic.rs` must be copied — not referenced — into
`shared_rust_services/src/tactical.rs`. The Rust code is pure math with no dependencies on
l0_ingest-specific types; the copy is semantically identical.

One function, `resolve_svol_fields`, exists only in the Python wrapper (no Rust equivalent).
It performs attribute access on `VannaFlowResult` objects, which are already PyO3 types from
`shared_rust.models`. This function is added to `shared_rust_services/src/tactical.rs` as
`tactical_resolve_svol_fields` using PyO3's dynamic attribute API.

## What Changes

### `shared_rust_services/src/tactical.rs` — NEW FILE (verbatim copy + one addition)

Copy all content from `l0_ingest/l0_rust/src/tactical_triad_logic.rs` verbatim, then add:

```rust
#[pyfunction]
#[pyo3(signature = (vanna_result=None))]
fn tactical_resolve_svol_fields(
    py: Python<'_>,
    vanna_result: Option<PyObject>,
) -> PyResult<(Option<f64>, String)> {
    let Some(result) = vanna_result else {
        return Ok((None, "UNAVAILABLE".to_string()));
    };
    let result = result.bind(py);
    let state_str: Option<String> = match result.getattr("state") {
        Ok(state_obj) if !state_obj.is_none() => match state_obj.getattr("value") {
            Ok(v) if !v.is_none() => v.str().ok().map(|s| s.to_string()),
            _ => state_obj.str().ok().map(|s| s.to_string()),
        },
        _ => None,
    };
    let state = normalize_svol_state_impl(state_str.as_deref());
    let corr: Option<f64> = match result.getattr("correlation") {
        Ok(c) if !c.is_none() => c.extract::<f64>().ok().filter(|v| v.is_finite()),
        _ => None,
    };
    match corr {
        None => Ok((None, "UNAVAILABLE".to_string())),
        Some(c) => Ok((Some(c), state)),
    }
}
```

Add `wrap_pyfunction!(tactical_resolve_svol_fields, module)?` to the `register` function.

### `shared_rust_services/src/lib.rs` — MODIFIED

Add `mod tactical;` to the module declarations.
Add `tactical::register(py, m)?;` inside the `services` pymodule function.

### `shared_rust/services.pyd` — REBUILT

Rebuild from `shared_rust_services` using the writable cargo target at
`C:\Users\Lenovo\.codex\memories\cargo_target\shared_rust_services`.
Copy output `services.dll` → `shared_rust/services.pyd`.

### `l0_ingest/l0_rust/src/tactical_triad_logic.rs` — NOT CHANGED

The original file is left intact. `l0_rust.tactical_*` exports remain available during
the transition window. Removal from `l0_rust` is deferred to a future session after
`impl-20260402-tactical-triad-wrapper-retirement` is fully closed.

## Scope

In:
- `shared_rust_services/src/tactical.rs` — new file
- `shared_rust_services/src/lib.rs` — two-line addition
- `shared_rust/services.pyd` — rebuild required

Out:
- `l0_ingest/l0_rust/src/tactical_triad_logic.rs` — not changed
- `shared/system/tactical_triad_logic.py` — not changed (retirement is next proposal)
- All consumer files — not changed (retirement is next proposal)
- `shared_rust/contracts.pyd`, `shared_rust/models.pyd` — not touched

## Hard Governance Prohibitions

- `shared_rust_services/src/tactical.rs` must not `use` any types from `l0_ingest` crate.
- `tactical_resolve_svol_fields` must not `unwrap()`. All attribute access must use `?` or `match`.
- The existing `l0_rust.tactical_*` exports must not be removed in this session.
- No new Python shim or wrapper file may be introduced.

## Verification Gate

1. `cargo build --release --target-dir C:\Users\Lenovo\.codex\memories\cargo_target\shared_rust_services` in `shared_rust_services/` — must pass with 0 errors.
2. `python -c "from shared_rust.services import tactical_compute_vrp, tactical_classify_vrp_state, tactical_normalize_svol_state, tactical_resolve_svol_fields, tactical_triad_spec; print('tactical-export-ok')"` — must print `tactical-export-ok`.
3. Behavioral parity check:
   - `python -c "from shared_rust.services import tactical_compute_vrp; assert tactical_compute_vrp(0.18, 13.5) is not None; print('vrp-ok')"` — must pass.
   - `python -c "from shared_rust.services import tactical_classify_vrp_state; assert tactical_classify_vrp_state(3.0) == 'EXPENSIVE'; print('classify-ok')"` — must pass.
   - `python -c "from shared_rust.services import tactical_normalize_svol_state; assert tactical_normalize_svol_state('NORMAL') == 'NORMAL'; assert tactical_normalize_svol_state(None) == 'UNAVAILABLE'; print('svol-ok')"` — must pass.
4. `powershell -ExecutionPolicy Bypass -File scripts/validate_session.ps1 -Strict` must pass.

## Rollback

Restore `shared_rust/services.pyd` from the pre-build backup (created before Step 3 in tasks.md).
`shared_rust_services/src/tactical.rs` deletion and `lib.rs` revert via `git restore`.
Zero consumer code was changed, so rollback has zero blast radius on running code.

## Risk

MEDIUM. Requires a Rust build and `.pyd` artifact replacement. Risk vectors:
- `cargo build` failure due to PyO3 version mismatch — mitigated by targeting exact same
  `shared_rust_services` workspace already used in Wave 18.
- `tactical_resolve_svol_fields` attribute access raises `PyErr` at runtime — mitigated by
  using `match`/`ok()` throughout with explicit `None` fallbacks.

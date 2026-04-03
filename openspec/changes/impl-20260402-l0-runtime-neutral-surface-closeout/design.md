## Open Gate Details

### Sub-wave F — Dual-Run Evidence Protocol

**Requirement:** One full US market session (09:30–16:00 ET) with both gateways active.

**Pre-conditions already met (2026-04-02):**

| Check | Evidence | Status |
|---|---|---|
| Rust gateway connectivity | REST rows=1, stream rows=21, `transport=arrow_ipc_named_event` | PASS |
| Rust gateway diagnostics | `connected=true`, `rust_started=true`, `status=OK` | PASS |
| get_oi_delta keyword fix | FlowEngineG rebuilt in services.pyd 2026-04-02 14:35 ET | PASS |
| _native_generated.l0_rust path fix | HeaderVolatilityContextService retargeted to native_loader | PASS |
| E2E smoke test | test_l0_l4_pipeline.py PASS, `dashboard_init` with `rust_active=True` | PASS |

**Evidence to collect during live session:**

1. Runtime log excerpt showing both gateways active for ≥ 60 contiguous minutes.
2. Sample of ≥ 10 `EnrichedSnapshot` outputs from Python gateway and Rust gateway at
   matched timestamps (±1 second tolerance).
3. Divergence table: for each of `net_gex`, `net_vanna`, `net_charm`, `call_wall`, `put_wall`,
   compute `max(abs(rust - python) / max(abs(python), 1e-8))` across the sample.
   All values must be < 0.0001 (0.01%).

**Command to capture diagnostics snapshot:**
```bash
curl -s http://127.0.0.1:8001/debug/persistence_status | python -m json.tool
```

### Sub-wave G — Full Test Suite

**Blocker resolved:** `tmp/pytest_cache` ACL repaired 2026-04-02.
- Lenovo user granted `(OI)(CI)(F)` with `/T /C`
- `icacls /reset /T /C` re-applied inheritance from repo root (two sandbox SIDs now present)

**Command:**
```bash
pwsh scripts/test/run_pytest.ps1 tests/l0_runtime/
```

If `tests/l0_runtime/` path does not exist, use:
```bash
pwsh scripts/test/run_pytest.ps1 l0_ingest/tests/
```

**Expected result:** all tests pass. The E2E smoke already passed 2026-04-02 14:42 ET.

### Remaining 28 Python Files — Intentional Non-Shim Classification

The following files remain in `shared/services/l0_runtime/` after sub-waves A–G. They
are NOT neutral-surface shims. Each contains Python coordination logic that cannot be
trivially replaced by a Rust callable without FFI complexity or Python startup semantics.

| File | Lines (est.) | Role | Retirement requirement |
|---|---|---|---|
| `native_loader.py` | ~40 | Singleton pyd loader; prevents RustIngestGateway collision | Rust singleton semantics in pyd |
| `normalize/*/__init__.py` (4) | ~10 each | Package entrypoints; no logic | None (keep forever) |
| `projection/*/__init__.py` (2) | ~10 each | Package entrypoints | None |
| `state/*/__init__.py` (2) | ~10 each | Package entrypoints | None |
| `services/__init__.py` + subpackage `__init__.py` (7) | ~30 each | Coordinator entrypoints | None |
| `services/_native_helpers.py` | ~200 | Quote API + profile binding; Python-side coordination | Dedicated Rust owner proposal |
| `services/sync/core.py` | ~150 | IV baseline sync state machine | Dedicated Rust owner proposal |
| `services/orchestration/feed_orchestrator.py` | ~80 | Startup stagger state machine | Dedicated Rust owner proposal |
| `source/runtime/_native_helpers.py` | ~150 | Quote profile + REST contract binding | Dedicated Rust owner proposal |
| `source/runtime/bootstrap.py` | ~100 | FeedBootstrap initialization | Dedicated Rust owner proposal |
| `source/runtime/ipc.py` | ~20 | IPC reader alias | Merge into entrypoint or keep |
| `_native/__init__.py` | ~5 | Empty stub for legacy path compat | Keep until all legacy paths retired |

Any future retirement of the four substantive helpers (`_native_helpers.py × 2`,
`sync/core.py`, `feed_orchestrator.py`) requires a new proposal with verified
Rust owner coverage per file.

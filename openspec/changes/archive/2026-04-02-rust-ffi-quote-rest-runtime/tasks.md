## 1. Rust FFI API

- [ ] 1.1 Add REST methods to `RustIngestGateway`.
- [ ] 1.2 Add calc-index name mapping and date parsing.
- [ ] 1.3 Remove runtime-path `unwrap()` from modified Rust file.

## 2. Python Runtime Adapter

- [ ] 2.1 Add async wrapper with `asyncio.to_thread`.
- [ ] 2.2 Normalize response rows into Python objects for existing consumers.
- [ ] 2.3 Surface explicit runtime diagnostics.

## 3. Verification

- [ ] 3.1 Add unit tests for runtime wrapper conversions and async non-blocking path.
- [ ] 3.2 Run L0 focused regressions via `scripts/test/run_pytest.ps1`.


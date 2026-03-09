## Context

Rust ingest already owns the high-frequency push path. This proposal extends the same owner to REST pulls needed by L0 orchestrators.

## Decisions

1. Reuse one `QuoteContext` inside `RustIngestGateway`.
2. Expose REST results as JSON rows through PyO3 methods to keep Python-side adapters lightweight.
3. Parse index names in Rust (`CalcIndex`) so Python can pass typed enums or names.

## Failure Handling

- Invalid date/index input returns explicit `PyRuntimeError`.
- Missing runtime context returns explicit error; no silent fallback.
- Start path removes runtime `unwrap()` usage in modified Rust file.


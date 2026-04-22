PARENT_CHANGE_ID: impl-20260402-l0-runtime-rust-cutover
DEPENDENCY_ORDER: 24
BLOCKED_BY: impl-20260402-l0-runtime-rust-cutover (sub-waves F+G gates open)

## Why

`impl-20260402-l0-runtime-rust-cutover` completed sub-waves A–E in full and landed all
code work for sub-waves F and G. Two formal gate closures remain:

**Sub-wave F — Dual-run evidence not yet recorded.**
All SPY.US MVP connectivity passes are confirmed (2026-04-02 12:44 ET and 14:18 ET):
`REST rows=1, stream rows=21, transport=arrow_ipc_named_event, rust_started=true`.
The runtime blockers (get_oi_delta keyword mismatch, _native_generated.l0_rust path) were
fixed in the same session. The evidence window requires one live US market session with
both gateways active simultaneously and a divergence comparison on chain aggregates.

**Sub-wave G — Full l0_runtime test suite not run.**
`pwsh scripts/test/run_pytest.ps1 tests/l0_runtime/` was blocked on 2026-04-02 by a
`tmp/pytest_cache` ACL ownership mismatch. The ACL has been repaired (2026-04-02 Lenovo
host: `icacls /grant Lenovo:(OI)(CI)(F) /T /C` + `icacls /reset /T /C`). The test suite
can now run.

Without these two closures the parent change record remains open and Sub-wave F divergence
risk is unquantified. This proposal closes both gates, records evidence, and declares the
l0_runtime Python neutral-surface retirement complete.

## What Changes

No new runtime code changes. This is a gate-closure session only:
1. Run the gated `tests/l0_runtime/` test suite.
2. Record Sub-wave F dual-run evidence during the next live US market session.
3. Update `impl-20260402-l0-runtime-rust-cutover/tasks.md` remaining [ ] items to [x].
4. Declare the 28 remaining Python coordinator files as intentional non-shims (not to be
   retired without a separate dedicated proposal and per-file Rust owner verification).

## Scope

In:
- `openspec/changes/impl-20260402-l0-runtime-rust-cutover/tasks.md` — close F+G remaining items
- `notes/sessions/2026-04-02/impl-20260402-l0-runtime-neutral-surface-closeout/` — evidence

Out:
- `shared/services/l0_runtime/` — zero code changes (28 files are intentional non-shims)
- `l0_ingest/l0_rust/` — no Rust source changes
- `shared_rust_l0_support/` — no changes

## Hard Governance Prohibitions

- Must not delete any of the 28 remaining l0_runtime Python files without a new, dedicated
  retirement proposal that verifies per-file Rust owner coverage.
- Must not re-introduce Python shims for paths retired in sub-waves A–G.
- Sub-wave F dual-run evidence must come from a live market session — synthetic comparison
  does not satisfy the gate.

## Verification Gate

1. `pwsh scripts/test/run_pytest.ps1 tests/l0_runtime/` → all tests pass
2. Sub-wave F dual-run: Python vs Rust gateway, same tick stream, ≥ 60 minutes of active
   overlap, field-level relative divergence < 0.01% on `net_gex/net_vanna/net_charm/
   call_wall/put_wall` of `EnrichedSnapshot.aggregates`
3. `pwsh scripts/validate_session.ps1 -Strict` → PASS

## Rollback

No code changes. Gate closure is documentation only; if evidence is insufficient, the
parent change remains open and sub-wave F/G items stay unchecked.

## Risk

LOW. No code changes. The two open gates are evidence-collection tasks, not implementation
tasks. The ACL blocker is resolved.

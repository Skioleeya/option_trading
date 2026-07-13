# Code Review — Dynamic Core Sentinel Subscriptions

## Remediation Status

- 2026-07-10: All listed findings were root-fixed.
- P1 resubscribe: `stop()` now clears applied subscription state, and `_sync_subscriptions()` only no-ops when runtime is started and writer-ready.
- P1 native loader: root/old-wave workaround was removed; current L0 native owner is `wave11/l0_rust.pyd`, and `build-pyd --crate l0_rust` installs directly to that owner.
- P2 step semantics: Rust selector now emits `call_core_step_range` / `put_core_step_range`; Python hysteresis requires those fields and compares true strike-ladder indexes.

## Findings

### P1 — Runtime can skip re-subscribe after disconnect while writer readiness is cleared

- File: `shared/services/l0_runtime/services/subscription/__init__.py`
- Lines: 309-317, 320-323
- Issue: `_sync_subscriptions()` returns early when `target_set == self._subscribed_symbols`, but `stop()` clears `_writer_ready_event` and does not clear `_subscribed_symbols`. If the manager is reused after disconnect/reconnect with the same target set, refresh no-ops, does not call runtime `subscribe()`, and does not set writer readiness. This can deadlock the Arrow startup gate or leave the runtime unsubscribed while Python believes targets are current.
- Plan impact: violates the plan/SOP requirement that `L0QuoteRuntime.subscribe()` receives the complete current symbol set and that Python target state must reflect actually applied runtime subscription state.
- Recommended fix: clear `_subscribed_symbols`/`_target_symbols` in `stop()`, or only apply the no-op when `is_rust_started and writer_ready` are both true. Add a regression for stop -> refresh same target.

### P1 — Native loader now prefers root artifact over versioned wave slots

- File: `shared/services/l0_runtime/native_loader.py`
- Lines: 16-25
- File: `shared/services/l0_runtime/services/_native_helpers.py`
- Lines: 12-22
- Issue: root `l0_rust.pyd` is now first in both default and services-specific loader candidates. The session handoff says this was done because `wave10/l0_rust.pyd` was locked. Since native artifacts are local runtime artifacts, this can cause other environments to load an older root artifact before a newer wave artifact, silently losing new exports or behavior.
- Plan impact: this is outside the subscription selection plan and weakens deterministic native owner resolution.
- Recommended fix: do not change global default loader order as a lock-file workaround. Prefer adding/installing a new versioned wave slot or fixing the build/install path to handle locked legacy slots without reordering production resolution.

### P2 — Rebalance “steps” are approximated with raw strike distance

- File: `shared/services/l0_runtime/services/subscription/selection.py`
- Lines: 58-60, 111-121
- Issue: `_core_shift_steps()` compares numeric strike differences, not strike index deltas from the current metadata ladder. This matches SPY if strikes are uniformly 1 point, but the plan says “档位” and the selector itself already reasons in strike steps during initial/core expansion.
- Plan impact: small but real semantic drift from `subscription_rebalance_min_shift_steps`.
- Recommended fix: compare range boundary indexes on the same sorted strike ladder used by Rust selection, or rename the config to point-distance if numeric strike distance is intentional.

## Checks Reviewed

- No L1/L2/L3 wall imports found in the changed subscription/orchestration files.
- Rust/Python changed runtime files remain under 400 lines.
- OpenSpec change exists and is linked in session metadata.
- Targeted tests and strict validation were recorded as passing.

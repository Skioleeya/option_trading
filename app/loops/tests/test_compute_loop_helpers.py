from __future__ import annotations

from app.loops.compute_loop import (
    _SnapshotVersionIvDriftProbe,
    _extract_runtime_spy_atm_iv,
    _extract_snapshot_version,
)


def test_extract_snapshot_version_accepts_int() -> None:
    assert _extract_snapshot_version({"version": 42}) == 42


def test_extract_snapshot_version_accepts_float() -> None:
    assert _extract_snapshot_version({"version": 42.9}) == 42


def test_extract_snapshot_version_accepts_numeric_string() -> None:
    assert _extract_snapshot_version({"version": "123"}) == 123


def test_extract_snapshot_version_rejects_invalid_values() -> None:
    assert _extract_snapshot_version({}) == 0
    assert _extract_snapshot_version({"version": None}) == 0
    assert _extract_snapshot_version({"version": "bad"}) == 0
    assert _extract_snapshot_version({"version": True}) == 0


def test_snapshot_iv_probe_confirms_after_three_ticks() -> None:
    probe = _SnapshotVersionIvDriftProbe(
        confirm_ticks=3,
        epsilon=1e-9,
        activate_lag_seconds=0.0,
        ongoing_log_interval_seconds=5.0,
    )

    probe.observe(snapshot_version=1, spy_atm_iv=0.25, now_monotonic=100.0)
    probe.observe(snapshot_version=2, spy_atm_iv=0.25, now_monotonic=101.0)
    probe.observe(snapshot_version=3, spy_atm_iv=0.25, now_monotonic=102.0)
    diag = probe.observe(snapshot_version=4, spy_atm_iv=0.25, now_monotonic=103.0)

    assert diag["drift_active"] is True
    assert diag["mismatch_count"] == 1
    assert diag["consecutive_drift_ticks"] == 3
    assert diag["current_lag_seconds"] == 2.0


def test_snapshot_iv_probe_recovers_and_resets_lag() -> None:
    probe = _SnapshotVersionIvDriftProbe(
        confirm_ticks=3,
        epsilon=1e-9,
        activate_lag_seconds=0.0,
        ongoing_log_interval_seconds=5.0,
    )

    probe.observe(snapshot_version=10, spy_atm_iv=0.2, now_monotonic=10.0)
    probe.observe(snapshot_version=11, spy_atm_iv=0.2, now_monotonic=11.0)
    probe.observe(snapshot_version=12, spy_atm_iv=0.2, now_monotonic=12.0)
    probe.observe(snapshot_version=13, spy_atm_iv=0.2, now_monotonic=13.0)
    probe.observe(snapshot_version=14, spy_atm_iv=0.2, now_monotonic=14.0)

    diag = probe.observe(snapshot_version=15, spy_atm_iv=0.21, now_monotonic=15.0)

    assert diag["drift_active"] is False
    assert diag["consecutive_drift_ticks"] == 0
    assert diag["current_lag_seconds"] == 0.0
    assert diag["last_completed_lag_seconds"] == 4.0
    assert diag["mismatch_count"] == 1


def test_snapshot_iv_probe_tolerates_invalid_inputs_without_crash() -> None:
    probe = _SnapshotVersionIvDriftProbe(
        confirm_ticks=3,
        epsilon=1e-9,
        activate_lag_seconds=0.0,
        ongoing_log_interval_seconds=5.0,
    )
    diag = probe.observe(snapshot_version="bad", spy_atm_iv=None, now_monotonic=1.0)

    assert diag["degraded_reason"] == "invalid_version_and_iv"
    assert diag["mismatch_count"] == 0
    assert diag["drift_active"] is False


def test_snapshot_iv_probe_requires_lag_seconds_before_activation() -> None:
    probe = _SnapshotVersionIvDriftProbe(
        confirm_ticks=3,
        epsilon=1e-9,
        activate_lag_seconds=10.0,
        ongoing_log_interval_seconds=5.0,
    )
    probe.observe(snapshot_version=1, spy_atm_iv=0.2, now_monotonic=100.0)
    probe.observe(snapshot_version=2, spy_atm_iv=0.2, now_monotonic=101.0)
    probe.observe(snapshot_version=3, spy_atm_iv=0.2, now_monotonic=102.0)
    diag = probe.observe(snapshot_version=4, spy_atm_iv=0.2, now_monotonic=103.0)
    assert diag["drift_active"] is False
    assert diag["current_lag_seconds"] == 2.0

    diag = probe.observe(snapshot_version=12, spy_atm_iv=0.2, now_monotonic=111.0)
    assert diag["drift_active"] is True
    assert diag["current_lag_seconds"] == 10.0
    assert diag["mismatch_count"] == 1


def test_extract_runtime_spy_atm_iv_prefers_l1_aggregates() -> None:
    class _Aggregates:
        atm_iv = 0.33

    class _L1Snapshot:
        aggregates = _Aggregates()

    class _Decision:
        data = {"spy_atm_iv": 0.25, "atm_iv": 0.24}

    value = _extract_runtime_spy_atm_iv(_L1Snapshot(), _Decision())
    assert value == 0.33


def test_extract_runtime_spy_atm_iv_falls_back_to_decision_data() -> None:
    class _L1Snapshot:
        aggregates = None

    class _Decision:
        data = {"spy_atm_iv": 0.27}

    value = _extract_runtime_spy_atm_iv(_L1Snapshot(), _Decision())
    assert value == 0.27


def test_extract_runtime_spy_atm_iv_returns_none_when_missing() -> None:
    class _L1Snapshot:
        aggregates = None

    class _Decision:
        data = {}

    value = _extract_runtime_spy_atm_iv(_L1Snapshot(), _Decision())
    assert value is None

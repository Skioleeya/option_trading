from __future__ import annotations

import pytest

from app.loops.compute_loop import (
    _SnapshotVersionIvDriftProbe,
    _build_l1_extra_metadata,
    _build_longport_option_diagnostics,
    _extract_runtime_spy_atm_iv,
    _extract_snapshot_version,
    _get_iv_sync_context,
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


def test_build_longport_option_diagnostics_summarizes_tier2_tier3_fields() -> None:
    snapshot = {
        "as_of_utc": "2026-03-12T15:10:00+00:00",
        "tier2_chain": [
            {"standard": True, "premium": 0.10},
            {"standard": False, "premium": 0.20},
        ],
        "tier3_chain": [
            {"standard": True, "premium": 0.30},
        ],
        "official_hv_diagnostics": {
            "official_hv_decimal": 0.18,
            "official_hv_sample_count": 12,
            "official_hv_synced_at_utc": "2026-03-12T15:05:00+00:00",
        },
    }

    diag = _build_longport_option_diagnostics(snapshot)

    assert diag["tier2_contracts"] == 2
    assert diag["tier3_contracts"] == 1
    assert diag["tier2_standard_ratio"] == 0.5
    assert diag["tier3_standard_ratio"] == 1.0
    assert diag["tier2_avg_premium"] == pytest.approx(0.15)
    assert diag["tier3_avg_premium"] == pytest.approx(0.30)
    assert diag["official_hv_decimal"] == pytest.approx(0.18)
    assert diag["official_hv_sample_count"] == 12
    assert diag["official_hv_synced_at_utc"] == "2026-03-12T15:05:00+00:00"
    assert diag["official_hv_age_sec"] == pytest.approx(300.0)


def test_build_l1_extra_metadata_includes_longport_option_diagnostics() -> None:
    snapshot = {
        "rust_active": True,
        "shm_stats": {"status": "OK"},
        "volume_map": {"560": 10},
        "as_of_utc": "2026-03-12T15:00:00+00:00",
        "tier2_chain": [{"standard": True, "premium": 0.10}],
        "tier3_chain": [{"standard": False, "premium": 0.20}],
        "official_hv_diagnostics": {
            "official_hv_decimal": 0.17,
            "official_hv_sample_count": 8,
            "official_hv_synced_at_utc": "2026-03-12T14:58:00+00:00",
        },
    }

    metadata = _build_l1_extra_metadata(snapshot, {"tick_id": 1})

    assert metadata["longport_option_diagnostics"]["tier2_contracts"] == 1
    assert metadata["longport_option_diagnostics"]["tier3_contracts"] == 1
    assert metadata["longport_option_diagnostics"]["tier2_standard_ratio"] == 1.0
    assert metadata["longport_option_diagnostics"]["tier3_standard_ratio"] == 0.0
    assert metadata["longport_option_diagnostics"]["official_hv_decimal"] == pytest.approx(0.17)
    assert metadata["longport_option_diagnostics"]["official_hv_sample_count"] == 8
    assert metadata["longport_option_diagnostics"]["official_hv_age_sec"] == pytest.approx(120.0)


def test_build_longport_option_diagnostics_handles_missing_official_hv() -> None:
    snapshot = {
        "as_of_utc": "2026-03-12T15:00:00+00:00",
        "tier2_chain": [],
        "tier3_chain": [],
        "official_hv_diagnostics": {},
    }

    diag = _build_longport_option_diagnostics(snapshot)

    assert diag["official_hv_decimal"] is None
    assert diag["official_hv_sample_count"] == 0
    assert diag["official_hv_synced_at_utc"] is None
    assert diag["official_hv_age_sec"] is None



def test_get_iv_sync_context_uses_public_builder_api() -> None:
    class _Builder:
        def get_iv_sync_context(self) -> tuple[dict[str, float], dict[str, float]]:
            return {"SPY.C": 0.22}, {"SPY.C": 560.0}

    iv_cache, spot_sync = _get_iv_sync_context(_Builder())

    assert iv_cache == {"SPY.C": 0.22}
    assert spot_sync == {"SPY.C": 560.0}


def test_get_iv_sync_context_returns_empty_when_api_missing() -> None:
    class _Builder:
        pass

    iv_cache, spot_sync = _get_iv_sync_context(_Builder())

    assert iv_cache == {}
    assert spot_sync == {}

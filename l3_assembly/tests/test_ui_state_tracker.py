from __future__ import annotations

from types import SimpleNamespace

import pytest

from l3_assembly.assembly.ui_state_tracker import UIStateTracker
from shared.config import settings


def _make_snapshot(
    atm_iv: float = 0.15,
    net_charm: float = 10.0,
    microstructure: dict[str, object] | None = None,
) -> SimpleNamespace:
    aggregates = SimpleNamespace(
        atm_iv=atm_iv,
        net_gex=1000.0,
        call_wall=600.0,
        put_wall=590.0,
        net_charm=net_charm,
    )
    return SimpleNamespace(
        spot=595.0,
        aggregates=aggregates,
        microstructure=microstructure or {},
    )


def test_tick_preserves_grind_stable_for_svol_state() -> None:
    tracker = UIStateTracker()
    out = tracker.tick(
        _make_snapshot(
            microstructure={
                "vanna_flow_result": {
                    "state": "GRIND_STABLE",
                    "correlation": -0.82,
                    "gex_regime": "DAMPING",
                }
            }
        ),
        decision=None,
    )

    assert out["svol_state"] == "GRIND_STABLE"
    assert out["svol_corr"] == pytest.approx(-0.82)
    assert out["gex_regime"] == "DAMPING"


def test_tick_marks_svol_unavailable_when_correlation_missing() -> None:
    tracker = UIStateTracker()
    out = tracker.tick(
        _make_snapshot(
            microstructure={
                "vanna_flow_result": {
                    "state": "UNAVAILABLE",
                    "correlation": None,
                }
            }
        ),
        decision=None,
    )

    assert out["svol_state"] == "UNAVAILABLE"
    assert out["svol_corr"] is None


def test_tick_normalizes_fractional_vrp_baseline_hv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "vrp_baseline_hv", 0.15)

    tracker = UIStateTracker()
    out = tracker.tick(_make_snapshot(atm_iv=0.15), decision=None)

    assert out["vrp"] == pytest.approx(0.0)
    assert out["vrp_state"] == "FAIR"


def test_tick_marks_skew_speculative_when_below_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "skew_speculative_max", -0.10)
    monkeypatch.setattr(settings, "skew_defensive_min", 0.15)

    tracker = UIStateTracker()
    decision = SimpleNamespace(
        feature_vector={"skew_25d_normalized": -0.30, "skew_25d_valid": 1.0},
        signal_summary={},
    )
    out = tracker.tick(_make_snapshot(), decision=decision)

    assert out["skew_dynamics"]["skew_state"] == "SPECULATIVE"
    assert out["skew_dynamics"]["skew_value"] == pytest.approx(-0.30)


def test_tick_marks_skew_defensive_when_above_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "skew_speculative_max", -0.10)
    monkeypatch.setattr(settings, "skew_defensive_min", 0.15)

    tracker = UIStateTracker()
    decision = SimpleNamespace(
        feature_vector={"skew_25d_normalized": 0.22, "skew_25d_valid": 1.0},
        signal_summary={},
    )
    out = tracker.tick(_make_snapshot(), decision=decision)

    assert out["skew_dynamics"]["skew_state"] == "DEFENSIVE"


def test_tick_marks_skew_unavailable_when_valid_flag_is_zero() -> None:
    tracker = UIStateTracker()
    decision = SimpleNamespace(
        feature_vector={"skew_25d_normalized": -0.33, "skew_25d_valid": 0.0},
        signal_summary={},
    )
    out = tracker.tick(_make_snapshot(), decision=decision)

    assert out["skew_dynamics"]["skew_state"] == "UNAVAILABLE"
    assert out["skew_dynamics"]["skew_value"] is None


def test_tick_prefers_snapshot_mtf_consensus_when_available() -> None:
    tracker = UIStateTracker()
    out = tracker.tick(
        _make_snapshot(
            microstructure={
                "mtf_consensus": {
                    "timeframes": {"1m": {"direction": "BULLISH"}},
                    "consensus": "BULLISH",
                    "strength": 0.88,
                    "alignment": 1.0,
                }
            }
        ),
        decision=None,
    )

    assert out["mtf_consensus"]["consensus"] == "BULLISH"
    assert out["mtf_consensus"]["strength"] == pytest.approx(0.88)
    assert out["mtf_consensus"]["alignment"] == pytest.approx(1.0)


def test_tick_wall_payload_preserves_history_series() -> None:
    tracker = UIStateTracker()
    out = tracker.tick(
        _make_snapshot(
            microstructure={
                "wall_migration": {
                    "call_wall_state": "REINFORCED_WALL",
                    "put_wall_state": "REINFORCED_SUPPORT",
                    "call_wall_history": [668.0, 669.0, 670.0],
                    "put_wall_history": [660.0, None, 659.0],
                }
            }
        ),
        decision=None,
    )

    wall = out["wall_migration_data"]
    assert wall["call_wall_state"] == "REINFORCED_WALL"
    assert wall["put_wall_state"] == "REINFORCED_SUPPORT"
    assert wall["call_wall_history"] == [668.0, 669.0, 670.0]
    assert wall["put_wall_history"] == [660.0, None, 659.0]


@pytest.mark.asyncio
async def test_set_redis_client_is_noop() -> None:
    tracker = UIStateTracker()
    await tracker.set_redis_client(object())

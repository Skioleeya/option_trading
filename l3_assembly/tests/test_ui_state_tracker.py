from __future__ import annotations

from types import SimpleNamespace

import pytest

from l3_assembly.assembly.ui_state_tracker import UIStateTracker
from shared.config import settings


class _FakeVannaResult:
    def __init__(self, state: str, correlation: float | None, gex_regime: str = "NEUTRAL") -> None:
        self.state = SimpleNamespace(value=state)
        self.correlation = correlation
        self.gex_regime = SimpleNamespace(value=gex_regime)
        self.wall_displacement_multiplier = 1.0


class _FakeVannaAnalyzer:
    def __init__(self, result: _FakeVannaResult) -> None:
        self._result = result

    def update(self, **_: object) -> _FakeVannaResult:
        return self._result


class _FakeWallResult:
    def model_dump(self) -> dict[str, str]:
        return {"call_wall_state": "STABLE", "put_wall_state": "STABLE"}


class _FakeWallTracker:
    def update(self, **_: object) -> _FakeWallResult:
        return _FakeWallResult()


class _FakeMTFEngine:
    def update(self, *_: object, **__: object) -> None:
        return None

    def compute(self, *_: object, **__: object) -> dict[str, object]:
        return {"consensus": "NEUTRAL", "alignment": 0.5}


def _make_snapshot(
    atm_iv: float = 0.15,
    net_charm: float = 10.0,
    mtf_consensus: dict[str, object] | None = None,
) -> SimpleNamespace:
    aggregates = SimpleNamespace(
        atm_iv=atm_iv,
        net_gex=1000.0,
        call_wall=600.0,
        put_wall=590.0,
        net_charm=net_charm,
    )
    microstructure = (
        SimpleNamespace(mtf_consensus=mtf_consensus) if mtf_consensus is not None else None
    )
    return SimpleNamespace(spot=595.0, aggregates=aggregates, microstructure=microstructure)


def _make_tracker(vanna_result: _FakeVannaResult) -> UIStateTracker:
    tracker = UIStateTracker()
    tracker._vanna_analyzer = _FakeVannaAnalyzer(vanna_result)  # type: ignore[attr-defined]
    tracker._wall_tracker = _FakeWallTracker()  # type: ignore[attr-defined]
    tracker._mtf_iv_engine = _FakeMTFEngine()  # type: ignore[attr-defined]
    return tracker


def test_tick_preserves_grind_stable_for_svol_state() -> None:
    tracker = _make_tracker(_FakeVannaResult(state="GRIND_STABLE", correlation=-0.82, gex_regime="DAMPING"))
    out = tracker.tick(_make_snapshot(), decision=None)

    assert out["svol_state"] == "GRIND_STABLE"
    assert out["svol_corr"] == pytest.approx(-0.82)


def test_tick_marks_svol_unavailable_when_correlation_missing() -> None:
    tracker = _make_tracker(_FakeVannaResult(state="UNAVAILABLE", correlation=None))
    out = tracker.tick(_make_snapshot(), decision=None)

    assert out["svol_state"] == "UNAVAILABLE"
    assert out["svol_corr"] is None


def test_tick_normalizes_fractional_vrp_baseline_hv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "vrp_baseline_hv", 0.15)

    tracker = _make_tracker(_FakeVannaResult(state="NORMAL", correlation=-0.2))
    out = tracker.tick(_make_snapshot(atm_iv=0.15), decision=None)

    assert out["vrp"] == pytest.approx(0.0)
    assert out["vrp_state"] == "FAIR"


def test_tick_marks_skew_speculative_when_below_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "skew_speculative_max", -0.10)
    monkeypatch.setattr(settings, "skew_defensive_min", 0.15)

    tracker = _make_tracker(_FakeVannaResult(state="NORMAL", correlation=-0.2))
    decision = SimpleNamespace(feature_vector={"skew_25d_normalized": -0.30}, signal_summary={})
    out = tracker.tick(_make_snapshot(), decision=decision)

    assert out["skew_dynamics"]["skew_state"] == "SPECULATIVE"
    assert out["skew_dynamics"]["skew_value"] == pytest.approx(-0.30)


def test_tick_marks_skew_defensive_when_above_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "skew_speculative_max", -0.10)
    monkeypatch.setattr(settings, "skew_defensive_min", 0.15)

    tracker = _make_tracker(_FakeVannaResult(state="NORMAL", correlation=-0.2))
    decision = SimpleNamespace(feature_vector={"skew_25d_normalized": 0.22}, signal_summary={})
    out = tracker.tick(_make_snapshot(), decision=decision)

    assert out["skew_dynamics"]["skew_state"] == "DEFENSIVE"


def test_tick_prefers_snapshot_mtf_consensus_when_available() -> None:
    tracker = _make_tracker(_FakeVannaResult(state="NORMAL", correlation=-0.2))
    out = tracker.tick(
        _make_snapshot(
            mtf_consensus={
                "timeframes": {"1m": {"direction": "BULLISH"}},
                "consensus": "BULLISH",
                "strength": 0.88,
                "alignment": 1.0,
            }
        ),
        decision=None,
    )

    assert out["mtf_consensus"]["consensus"] == "BULLISH"
    assert out["mtf_consensus"]["strength"] == pytest.approx(0.88)
    assert out["mtf_consensus"]["alignment"] == pytest.approx(1.0)

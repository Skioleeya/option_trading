from __future__ import annotations

from types import SimpleNamespace

from l3_assembly.assembly.ui_state_tracker import UIStateTracker
from shared.config import settings


def _decision(rr25: object, valid: float = 1.0) -> SimpleNamespace:
    return SimpleNamespace(
        feature_vector={
            "rr25_call_minus_put": rr25,
            "skew_25d_valid": valid,
        }
    )


def test_skew_rr25_config_keys_hard_cut() -> None:
    assert hasattr(settings, "skew_rr25_defensive_max")
    assert hasattr(settings, "skew_rr25_speculative_min")
    assert not hasattr(settings, "skew_speculative_max")
    assert not hasattr(settings, "skew_defensive_min")


def test_skew_dynamics_rr25_sign_mapping_and_boundaries(monkeypatch) -> None:
    monkeypatch.setattr(settings, "skew_rr25_defensive_max", -0.03, raising=True)
    monkeypatch.setattr(settings, "skew_rr25_speculative_min", 0.02, raising=True)

    defensive = UIStateTracker._extract_skew_dynamics(_decision(-0.05))
    assert defensive["skew_state"] == "DEFENSIVE"

    defensive_edge = UIStateTracker._extract_skew_dynamics(_decision(-0.03))
    assert defensive_edge["skew_state"] == "DEFENSIVE"

    neutral = UIStateTracker._extract_skew_dynamics(_decision(-0.01))
    assert neutral["skew_state"] == "NEUTRAL"

    speculative_edge = UIStateTracker._extract_skew_dynamics(_decision(0.02))
    assert speculative_edge["skew_state"] == "SPECULATIVE"

    speculative = UIStateTracker._extract_skew_dynamics(_decision(0.04))
    assert speculative["skew_state"] == "SPECULATIVE"


def test_skew_dynamics_unavailable_when_gate_or_rr25_invalid() -> None:
    invalid_gate = UIStateTracker._extract_skew_dynamics(_decision(-0.05, valid=0.0))
    assert invalid_gate == {"skew_value": None, "skew_state": "UNAVAILABLE"}

    invalid_value = UIStateTracker._extract_skew_dynamics(_decision("bad", valid=1.0))
    assert invalid_value == {"skew_value": None, "skew_state": "UNAVAILABLE"}

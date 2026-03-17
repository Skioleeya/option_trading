from __future__ import annotations

from dataclasses import dataclass

from l2_decision.agents.services.agent_g_decision_support import (
    build_micro_flow_signal,
    collect_atm_micro_metrics,
    extract_dealer_squeeze_alert,
    safe_get_value,
)


@dataclass
class _State:
    dealer_squeeze_alert: bool = False


def test_safe_get_value_supports_object_and_dict() -> None:
    payload = {"x": 1}
    assert safe_get_value(payload, "x", 0) == 1
    assert safe_get_value(payload, "missing", 9) == 9

    class Obj:
        x = 2

    assert safe_get_value(Obj(), "x", 0) == 2


def test_collect_atm_micro_metrics_uses_window() -> None:
    rows = [
        {"strike": 670.0, "toxicity_score": 0.6, "bbo_imbalance": 0.3, "vpin_score": 0.1},
        {"strike": 671.0, "toxicity_score": 0.2, "bbo_imbalance": 0.2, "vpin_score": 0.2},
        {"strike": 690.0, "toxicity_score": 5.0, "bbo_imbalance": 5.0, "vpin_score": 5.0},
    ]
    avg_tox, avg_bbo, avg_vpin = collect_atm_micro_metrics(per_strike=rows, spot=670.5)
    assert round(avg_tox, 3) == 0.4
    assert round(avg_bbo, 3) == 0.25
    assert round(avg_vpin, 3) == 0.15


def test_build_micro_flow_signal_and_dealer_squeeze_fallback() -> None:
    signal, avg_bbo = build_micro_flow_signal(
        avg_tox=0.6,
        avg_bbo=0.0,
        fallback_bbo=0.2,
        net_gex=-1.0,
        threshold=0.25,
    )
    assert signal["direction"] == "BULLISH"
    assert signal["confidence"] > 0.0
    assert avg_bbo == 0.2

    assert extract_dealer_squeeze_alert(_State(dealer_squeeze_alert=True), {}) is True
    assert extract_dealer_squeeze_alert(None, {"micro_structure": {"micro_structure_state": {"dealer_squeeze_alert": True}}}) is True
    assert extract_dealer_squeeze_alert(None, {"micro_structure": {"micro_structure_state": {}}}) is False


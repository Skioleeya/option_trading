from types import SimpleNamespace

import pytest

from l3_assembly.assembly.ui_state_tracker import UIStateTracker


def _decision() -> SimpleNamespace:
    return SimpleNamespace(
        signal_summary={"momentum_signal": "NEUTRAL"},
        feature_vector={},
    )


def _snapshot(gex_regime: object) -> SimpleNamespace:
    aggregates = SimpleNamespace(
        spot=679.5,
        atm_iv=0.22,
        net_charm_raw_sum=0.0,
        net_vanna_raw_sum=0.0,
    )
    vanna_flow_result = SimpleNamespace(
        state=SimpleNamespace(value="NORMAL"),
        correlation=0.0,
        gex_regime=gex_regime,
    )
    microstructure = SimpleNamespace(
        iv_velocity=None,
        wall_migration=None,
        wall_context=None,
        vanna_flow_result=vanna_flow_result,
        mtf_consensus=None,
        volume_imbalance=None,
        jump_detection=None,
        dealer_squeeze_alert=False,
        iv_confidence=0.0,
        wall_confidence=0.0,
        vanna_confidence=0.0,
    )
    return SimpleNamespace(
        spot=679.5,
        aggregates=aggregates,
        microstructure=microstructure,
    )


def test_tick_parses_string_gex_regime_from_object_path() -> None:
    out = UIStateTracker().tick(_snapshot("ACCELERATION"), _decision())
    assert out["gex_regime"] == "ACCELERATION"


def test_tick_parses_enum_like_gex_regime_from_object_path() -> None:
    out = UIStateTracker().tick(_snapshot(SimpleNamespace(value="DAMPING")), _decision())
    assert out["gex_regime"] == "DAMPING"


def test_tick_rejects_unknown_gex_regime() -> None:
    with pytest.raises(ValueError, match="Invalid gex_regime"):
        UIStateTracker().tick(_snapshot("BAD_STATE"), _decision())

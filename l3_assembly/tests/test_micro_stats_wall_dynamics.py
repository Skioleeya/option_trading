"""Tests for MicroStats wall dynamics state management."""

from l3_assembly.presenters.ui.micro_stats.wall_dynamics import classify_wall_key
from l3_assembly.presenters.ui.micro_stats import presenter as presenter_mod


def _reset_wall_debounce_state() -> None:
    presenter_mod._last_committed_wall_key = "STABLE"
    presenter_mod._pending_wall_key = ""
    presenter_mod._pending_wall_key_count = 0


def test_classify_wall_key_breach_priority():
    assert classify_wall_key("BREACHED", "REINFORCED_SUPPORT") == "BREACH"
    assert classify_wall_key("REINFORCED_WALL", "BREACHED") == "BREACH"


def test_classify_wall_key_decay_and_unavailable():
    assert classify_wall_key("DECAYING", "STABLE") == "DECAY"
    assert classify_wall_key("UNAVAILABLE", "UNAVAILABLE") == "UNAVAILABLE"


def test_classify_wall_key_retreat_is_directional():
    assert classify_wall_key("RETREATING_RESISTANCE", "STABLE") == "RETREAT_UP"
    assert classify_wall_key("STABLE", "RETREATING_SUPPORT") == "RETREAT_DOWN"


def test_classify_wall_key_collapse_requires_context_gate():
    low_flow = {
        "gamma_regime": "SHORT_GAMMA",
        "hedge_flow_intensity": 0.05,
    }
    high_flow = {
        "gamma_regime": "SHORT_GAMMA",
        "hedge_flow_intensity": 1.2,
    }
    assert classify_wall_key("STABLE", "RETREATING_SUPPORT", low_flow) == "RETREAT_DOWN"
    assert classify_wall_key("STABLE", "RETREATING_SUPPORT", high_flow) == "COLLAPSE"


def test_presenter_breach_bypasses_debounce():
    _reset_wall_debounce_state()
    out = presenter_mod.MicroStatsPresenter.build(
        gex_regime="NEUTRAL",
        wall_dyn={"call_wall_state": "BREACHED", "put_wall_state": "STABLE"},
        vanna="NORMAL",
        momentum="NEUTRAL",
    )
    assert out["wall_dyn"]["label"] == "BREACH"
    assert out["wall_dyn"]["badge"] == "badge-amber"


def test_presenter_non_urgent_keeps_debounce():
    _reset_wall_debounce_state()
    first = presenter_mod.MicroStatsPresenter.build(
        gex_regime="NEUTRAL",
        wall_dyn={"call_wall_state": "REINFORCED_WALL", "put_wall_state": "REINFORCED_SUPPORT"},
        vanna="NORMAL",
        momentum="NEUTRAL",
    )
    second = presenter_mod.MicroStatsPresenter.build(
        gex_regime="NEUTRAL",
        wall_dyn={"call_wall_state": "REINFORCED_WALL", "put_wall_state": "REINFORCED_SUPPORT"},
        vanna="NORMAL",
        momentum="NEUTRAL",
    )
    assert first["wall_dyn"]["label"] == "STABLE"
    assert second["wall_dyn"]["label"] == "PINCH"


def test_presenter_retreat_down_commits_without_debounce():
    _reset_wall_debounce_state()
    out = presenter_mod.MicroStatsPresenter.build(
        gex_regime="NEUTRAL",
        wall_dyn={"call_wall_state": "STABLE", "put_wall_state": "RETREATING_SUPPORT"},
        vanna="NORMAL",
        momentum="NEUTRAL",
    )
    assert out["wall_dyn"]["label"] == "RETREAT ↓"
    assert out["wall_dyn"]["badge"] == "badge-green"


def test_presenter_collapse_commits_without_debounce():
    _reset_wall_debounce_state()
    wall_dyn = {
        "call_wall_state": "STABLE",
        "put_wall_state": "RETREATING_SUPPORT",
        "wall_context": {
            "gamma_regime": "SHORT_GAMMA",
            "hedge_flow_intensity": 1.5,
        },
    }
    first = presenter_mod.MicroStatsPresenter.build(
        gex_regime="NEUTRAL",
        wall_dyn=wall_dyn,
        vanna="NORMAL",
        momentum="NEUTRAL",
    )
    second = presenter_mod.MicroStatsPresenter.build(
        gex_regime="NEUTRAL",
        wall_dyn=wall_dyn,
        vanna="NORMAL",
        momentum="NEUTRAL",
    )
    assert first["wall_dyn"]["label"] == "COLLAPSE"
    assert second["wall_dyn"]["label"] == "COLLAPSE"

"""Tests for Phase 4: L3AssemblyReactor end-to-end."""
import asyncio
import pytest
from datetime import datetime, timezone

from l3_assembly.events.payload_events import FrozenPayload, UIState, SignalData
from l3_assembly.reactor import L3AssemblyReactor


class _MockDecision:
    def __init__(self, direction="BULLISH", version=10, feature_vector=None, signal_summary=None):
        self.direction = direction
        self.confidence = 0.75
        self.pre_guard_direction = "BULLISH"
        self.guard_actions = []
        self.signal_summary = signal_summary or {"gex_regime": "SUPER_PIN", "atm_iv": "0.12"}
        self.fusion_weights = {"momentum": 0.4}
        self.latency_ms = 12.0
        self.version = version
        self.computed_at = datetime.now(timezone.utc)
        self.feature_vector = dict(feature_vector or {})


class _MockSnapshot:
    def __init__(self, spot=560.0, version=10, microstructure=None):
        self.spot = spot
        self.chain = []
        self.computed_at = datetime.now(timezone.utc)
        self.microstructure = microstructure or {}
        class _Aggs:
            flip_level = 558.0
            net_gex = 1.5e9
            atm_iv = 0.125
            net_charm = 5.2
        self.aggregates = _Aggs()


# ─────────────────────────────────────────────────────────────────────────────
# L3AssemblyReactor tests
# ─────────────────────────────────────────────────────────────────────────────

class TestL3AssemblyReactor:
    def test_tick_returns_frozen_payload(self):
        reactor = L3AssemblyReactor()
        result = asyncio.run(reactor.tick(_MockDecision(), _MockSnapshot()))
        assert isinstance(result, FrozenPayload)

    def test_tick_spot_correct(self):
        reactor = L3AssemblyReactor()
        result = asyncio.run(reactor.tick(_MockDecision(), _MockSnapshot(spot=575.0)))
        assert result.spot == 575.0

    def test_tick_version_propagated(self):
        reactor = L3AssemblyReactor()
        result = asyncio.run(reactor.tick(_MockDecision(version=99), _MockSnapshot()))
        assert result.version == 99

    def test_tick_stores_to_hot_layer(self):
        reactor = L3AssemblyReactor()
        asyncio.run(reactor.tick(_MockDecision(), _MockSnapshot()))
        assert reactor.store.hot_size() == 1

    def test_tick_none_decision_no_crash(self):
        """None decision must return safe neutral payload, not raise."""
        reactor = L3AssemblyReactor()
        result = asyncio.run(reactor.tick(None, _MockSnapshot()))
        assert isinstance(result, FrozenPayload)
        assert result.signal.direction == "NEUTRAL"

    def test_tick_with_atm_decay(self):
        reactor = L3AssemblyReactor()
        atm = {"anchor_strike": 560.0, "current_iv": 0.12}
        result = asyncio.run(reactor.tick(_MockDecision(), _MockSnapshot(), atm_decay=atm))
        assert result.atm == atm

    def test_multiple_ticks_increment_counter(self):
        reactor = L3AssemblyReactor()
        for i in range(5):
            asyncio.run(reactor.tick(_MockDecision(version=i), _MockSnapshot()))
        assert reactor._total_ticks == 5
        assert reactor.store.hot_size() == 5

    def test_to_dict_legacy_schema_compatibility(self):
        """FrozenPayload.to_dict() must contain all keys expected by legacy frontend."""
        reactor = L3AssemblyReactor()
        result = asyncio.run(reactor.tick(_MockDecision(), _MockSnapshot()))
        d = result.to_dict()

        # Required top-level keys
        for key in ("type", "spot", "data_timestamp", "timestamp", "drift_ms", "is_stale"):
            assert key in d, f"Missing key: {key}"

        # agent_g.data.ui_state path
        assert "agent_g" in d
        assert "data" in d["agent_g"]
        assert "ui_state" in d["agent_g"]["data"]
        ui = d["agent_g"]["data"]["ui_state"]
        for section in ("micro_stats", "tactical_triad", "wall_migration",
                        "depth_profile", "active_options", "mtf_flow"):
            assert section in ui, f"Missing ui_state.{section}"

    def test_get_diagnostics_schema(self):
        reactor = L3AssemblyReactor()
        asyncio.run(reactor.tick(_MockDecision(), _MockSnapshot()))
        diag = reactor.get_diagnostics()
        assert "l3_reactor" in diag
        assert "l3_store" in diag
        assert "total_ticks" in diag["l3_reactor"]
        assert "delta_ratio" in diag["l3_reactor"]

    def test_with_broadcast_fields_workflow(self):
        """Simulate what AppContainer._broadcast_loop does with the result."""
        reactor = L3AssemblyReactor()
        frozen = asyncio.run(reactor.tick(_MockDecision(), _MockSnapshot()))
        updated = frozen.with_broadcast_fields(
            heartbeat_timestamp="2026-03-04T09:30:01+00:00",
            is_stale=False,
        )
        d = updated.to_dict()
        assert d["heartbeat_timestamp"] == "2026-03-04T09:30:01+00:00"
        assert d["is_stale"] is False

    def test_exception_recovery_returns_safe_payload(self):
        """If assembler raises, reactor should return safe neutral payload."""
        reactor = L3AssemblyReactor()
        # Pass completely broken snapshot that triggers exception path
        bad_snapshot = "THIS_IS_NOT_A_VALID_SNAPSHOT"
        result = asyncio.run(reactor.tick(_MockDecision(), bad_snapshot))
        # Must NOT raise — must return safe payload
        assert isinstance(result, FrozenPayload)

    def test_dual_snapshot_dict_input(self):
        """Reactor should work with legacy dict snapshot (gradual migration path)."""
        reactor = L3AssemblyReactor()
        dict_snap = {"spot": 562.5, "chain": [], "as_of": datetime.now(timezone.utc).isoformat()}
        result = asyncio.run(reactor.tick(_MockDecision(), dict_snap))
        assert result.spot == 562.5

    def test_active_options_contract_preserves_impact_and_sweep(self):
        reactor = L3AssemblyReactor()
        active_options = [{
            "symbol": "SPY",
            "option_type": "C",
            "strike": 560.0,
            "implied_volatility": 0.12,
            "volume": 50000,
            "turnover": 1e7,
            "flow": 2.5,
            "impact_index": 88.1234,
            "is_sweep": True,
            "flow_deg_formatted": "$1.0M",
            "flow_volume_label": "50K",
            "flow_color": "text-accent-red",
            "flow_glow": "",
            "flow_intensity": "HIGH",
            "flow_direction": "BULLISH",
            "flow_d_z": 1.2,
            "flow_e_z": 0.8,
            "flow_g_z": 0.5,
        }]
        result = asyncio.run(
            reactor.tick(_MockDecision(), _MockSnapshot(), active_options=active_options)
        )
        row = result.to_dict()["agent_g"]["data"]["ui_state"]["active_options"][0]
        assert row["impact_index"] == pytest.approx(88.1234)
        assert row["is_sweep"] is True
        assert row["option_type"] == "CALL"

    def test_cross_layer_contract_regression_ui_state_fields(self):
        reactor = L3AssemblyReactor()
        decision = _MockDecision(
            feature_vector={"skew_25d_normalized": -0.33},
            signal_summary={
                "gex_regime": "ACCELERATION",
                "atm_iv": "0.12",
                "momentum_signal": {"direction": "BULLISH"},
            },
        )
        snapshot = _MockSnapshot(
            microstructure={
                "vanna_flow_result": {
                    "state": "DANGER_ZONE",
                    "correlation": 0.31,
                    "gex_regime": "ACCELERATION",
                },
                "wall_migration": {
                    "call_wall_state": "REINFORCED",
                    "put_wall_state": "RETREAT",
                },
                "mtf_consensus": {
                    "timeframes": {
                        "1m": {"direction": "BULLISH", "regime": "BREAKOUT", "z": 1.8, "strength": 0.90},
                        "5m": {"direction": "BULLISH", "regime": "DRIFT_UP", "z": 1.1, "strength": 0.72},
                        "15m": {"direction": "NEUTRAL", "regime": "NOISE", "z": 0.1, "strength": 0.30},
                    },
                    "consensus": "BULLISH",
                    "strength": 0.82,
                    "alignment": 0.9,
                },
            }
        )
        active_options = [
            {
                "symbol": "SPY",
                "option_type": "C",
                "strike": 560.0,
                "implied_volatility": 0.22,
                "volume": 50000,
                "turnover": 1e7,
                "flow": 2.5,
                "impact_index": 88.1234,
                "is_sweep": True,
                "flow_deg_formatted": "$1.0M",
                "flow_volume_label": "50K",
                "flow_color": "text-accent-red",
                "flow_glow": "",
                "flow_intensity": "HIGH",
                "flow_direction": "BULLISH",
                "flow_d_z": 1.2,
                "flow_e_z": 0.8,
                "flow_g_z": 0.5,
            },
            {
                "symbol": "SPY",
                "option_type": "P",
                "strike": 559.0,
                "implied_volatility": 0.24,
                "volume": 41000,
                "turnover": 0.8e7,
                "flow": -1.8,
                "impact_index": 77.7777,
                "is_sweep": False,
                "flow_deg_formatted": "$0.8M",
                "flow_volume_label": "41K",
                "flow_color": "text-accent-green",
                "flow_glow": "",
                "flow_intensity": "MODERATE",
                "flow_direction": "BEARISH",
                "flow_d_z": 1.0,
                "flow_e_z": 0.6,
                "flow_g_z": 0.3,
            },
        ]

        result = asyncio.run(
            reactor.tick(decision, snapshot, active_options=active_options)
        )
        ui_state = result.to_dict()["agent_g"]["data"]["ui_state"]

        assert ui_state["skew_dynamics"]["state_label"] == "SPECULATIVE"
        assert ui_state["skew_dynamics"]["value"] == "-0.33"

        mtf_flow = ui_state["mtf_flow"]
        for key in ("m1", "m5", "m15", "consensus", "strength", "alignment", "align_label", "align_color"):
            assert key in mtf_flow
        assert mtf_flow["consensus"] == "BULLISH"

        tactical_triad = ui_state["tactical_triad"]
        for leg in ("vrp", "charm", "svol"):
            assert leg in tactical_triad
            for field in ("value", "state_label", "color_class", "border_class", "bg_class", "shadow_class"):
                assert field in tactical_triad[leg]
            for field in ("sub_intensity", "sub_label"):
                assert field in tactical_triad[leg]

        row0, row1 = ui_state["active_options"][:2]
        assert row0["option_type"] == "CALL"
        assert row1["option_type"] == "PUT"
        assert row0["impact_index"] == pytest.approx(88.1234)
        assert row0["is_sweep"] is True

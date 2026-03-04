"""Tests for Phase 4: L3AssemblyReactor end-to-end."""
import asyncio
import pytest
from datetime import datetime, timezone

from l3_assembly.events.payload_events import FrozenPayload, UIState, SignalData
from l3_assembly.reactor import L3AssemblyReactor


class _MockDecision:
    def __init__(self, direction="BULLISH", version=10):
        self.direction = direction
        self.confidence = 0.75
        self.pre_guard_direction = "BULLISH"
        self.guard_actions = []
        self.signal_summary = {"gex_regime": "SUPER_PIN", "atm_iv": "0.12"}
        self.fusion_weights = {"momentum": 0.4}
        self.latency_ms = 12.0
        self.version = version
        self.computed_at = datetime.now(timezone.utc)


class _MockSnapshot:
    def __init__(self, spot=560.0, version=10):
        self.spot = spot
        self.chain = []
        self.computed_at = datetime.now(timezone.utc)
        class _Aggs:
            flip_level = 558.0
            net_gex = 1.5e9
            atm_iv = 0.125
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

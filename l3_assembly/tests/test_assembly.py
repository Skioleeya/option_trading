"""Tests for Phase 3: PayloadAssemblerV2 + FieldDeltaEncoder + TimeSeriesStoreV2."""
import asyncio
import dataclasses
import pytest
from datetime import datetime, timezone

from l3_assembly.events.payload_events import (
    FrozenPayload, UIState, SignalData, MicroStatsState, TacticalTriadState,
    MTFFlowState, MetricCard,
)
from l3_assembly.events.delta_events import DeltaPayload, DeltaType
from l3_assembly.assembly.payload_assembler import PayloadAssemblerV2
from l3_assembly.assembly.delta_encoder import FieldDeltaEncoder
from l3_assembly.storage.timeseries_store import TimeSeriesStoreV2
from l3_assembly.presenters.ui.micro_stats import presenter as micro_presenter_mod


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_signal(version: int = 1, direction: str = "NEUTRAL") -> SignalData:
    return SignalData(
        direction=direction, confidence=0.55,
        pre_guard_direction="NEUTRAL", guard_actions=(),
        signal_summary={}, fusion_weights={},
        latency_ms=5.0, version=version,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )


def _make_frozen(version: int = 1, spot: float = 560.0) -> FrozenPayload:
    return FrozenPayload(
        data_timestamp=datetime.now(timezone.utc).isoformat(),
        broadcast_timestamp=datetime.now(timezone.utc).isoformat(),
        spot=spot,
        version=version,
        drift_ms=5.0,
        drift_warning=False,
        signal=_make_signal(version),
        ui_state=UIState.zero_state(),
        atm=None,
    )


def _reset_micro_stats_wall_debounce_state() -> None:
    micro_presenter_mod._last_committed_wall_key = "STABLE"
    micro_presenter_mod._pending_wall_key = ""
    micro_presenter_mod._pending_wall_key_count = 0


class _MockDecision:
    """Stand-in for L2 DecisionOutput."""
    def __init__(self, direction="NEUTRAL", version=1):
        self.direction = direction
        self.confidence = 0.6
        self.pre_guard_direction = "NEUTRAL"
        self.guard_actions = []
        self.signal_summary = {"gex_regime": "NEUTRAL"}
        self.fusion_weights = {}
        self.latency_ms = 8.0
        self.version = version
        self.computed_at = datetime.now(timezone.utc)


class _MockSnapshot:
    """Stand-in for L1 EnrichedSnapshot (minimal)."""
    def __init__(self, spot=560.0):
        self.spot = spot
        self.chain = []
        self.computed_at = datetime.now(timezone.utc)
        self.extra_metadata = {}
        class _Aggs:
            flip_level = 558.0
            net_gex = 1e9
            atm_iv = 0.12
        self.aggregates = _Aggs()


# ─────────────────────────────────────────────────────────────────────────────
# PayloadAssemblerV2 tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPayloadAssemblerV2:
    def test_returns_frozen_payload(self):
        assembler = PayloadAssemblerV2()
        result = assembler.assemble(_MockDecision(), _MockSnapshot(), None, ())
        assert isinstance(result, FrozenPayload)

    def test_spot_extracted_from_typed_snapshot(self):
        assembler = PayloadAssemblerV2()
        result = assembler.assemble(_MockDecision(), _MockSnapshot(spot=575.0), None, ())
        assert result.spot == 575.0

    def test_spot_extracted_from_dict_snapshot(self):
        assembler = PayloadAssemblerV2()
        result = assembler.assemble(_MockDecision(), {"spot": 562.5, "chain": []}, None, ())
        assert result.spot == 562.5

    def test_version_propagated(self):
        assembler = PayloadAssemblerV2()
        result = assembler.assemble(_MockDecision(version=99), _MockSnapshot(), None, ())
        assert result.version == 99

    def test_macro_volume_map_propagates_from_typed_snapshot_metadata(self):
        assembler = PayloadAssemblerV2()
        snap = _MockSnapshot()
        snap.extra_metadata = {
            "volume_map": {
                "560.0": 12345,
                561.0: 6789,
                "bad_strike": 100,
                "562.0": "bad_volume",
            }
        }

        result = assembler.assemble(_MockDecision(), snap, None, ())
        assert result.ui_state.macro_volume_map == {
            "560.0": 12345.0,
            "561.0": 6789.0,
        }

    def test_micro_stats_preserve_wall_dyn_and_badge_tokens(self):
        _reset_micro_stats_wall_debounce_state()
        assembler = PayloadAssemblerV2()
        ui_metrics = {
            "gex_regime": "DAMPING",
            "vanna_state": "DANGER_ZONE",
            "momentum": "BULLISH",
            "wall_migration_data": {
                "call_wall_state": "REINFORCED_WALL",
                "put_wall_state": "REINFORCED_SUPPORT",
            },
        }

        # First tick seeds the wall-dyn debounce state; second tick should commit PINCH.
        assembler.assemble(_MockDecision(), _MockSnapshot(), None, (), ui_metrics)
        result = assembler.assemble(_MockDecision(), _MockSnapshot(), None, (), ui_metrics)
        micro = result.ui_state.micro_stats.to_dict()

        assert micro["wall_dyn"]["label"] == "PINCH"
        assert micro["wall_dyn"]["badge"] == "badge-purple"
        assert micro["net_gex"]["badge"] == "badge-hollow-green"
        assert micro["vanna"]["badge"] == "badge-red"
        assert micro["momentum"]["badge"] == "badge-red"

    def test_micro_stats_wall_context_can_gate_collapse(self):
        _reset_micro_stats_wall_debounce_state()
        assembler = PayloadAssemblerV2()
        ui_metrics = {
            "gex_regime": "NEUTRAL",
            "vanna_state": "NORMAL",
            "momentum": "NEUTRAL",
            "wall_migration_data": {
                "call_wall_state": "STABLE",
                "put_wall_state": "RETREATING_SUPPORT",
                "wall_context": {
                    "gamma_regime": "SHORT_GAMMA",
                    "hedge_flow_intensity": 2.0,
                },
            },
        }

        assembler.assemble(_MockDecision(), _MockSnapshot(), None, (), ui_metrics)
        result = assembler.assemble(_MockDecision(), _MockSnapshot(), None, (), ui_metrics)
        micro = result.ui_state.micro_stats.to_dict()
        assert micro["wall_dyn"]["label"] == "COLLAPSE"

    def test_micro_stats_retreat_direction_matches_wall_migration_same_tick(self):
        _reset_micro_stats_wall_debounce_state()
        assembler = PayloadAssemblerV2()
        ui_metrics = {
            "gex_regime": "NEUTRAL",
            "vanna_state": "NORMAL",
            "momentum": "NEUTRAL",
            "wall_migration_data": {
                "call_wall_state": "STABLE",
                "put_wall_state": "RETREATING_SUPPORT",
                "call_wall_history": [602.0, 603.0, 604.0],
                "put_wall_history": [595.0, 594.0, 593.0],
                "wall_context": {
                    "gamma_regime": "SHORT_GAMMA",
                    "hedge_flow_intensity": 0.1,
                },
            },
        }

        result = assembler.assemble(_MockDecision(), _MockSnapshot(), None, (), ui_metrics)
        micro = result.ui_state.micro_stats.to_dict()
        wall_rows = result.ui_state.wall_migration
        assert micro["wall_dyn"]["label"] == "RETREAT ↓"
        assert micro["wall_dyn"]["badge"] == "badge-green"
        assert len(wall_rows) == 2
        assert wall_rows[1].lights.get("wall_dyn_badge") == "RETREAT ↓"

    def test_none_decision_produces_neutral(self):
        assembler = PayloadAssemblerV2()
        result = assembler.assemble(None, _MockSnapshot(), None, ())
        assert isinstance(result, FrozenPayload)
        assert result.signal.direction == "NEUTRAL"

    def test_ui_state_is_frozen(self):
        assembler = PayloadAssemblerV2()
        result = assembler.assemble(_MockDecision(), _MockSnapshot(), None, ())
        assert isinstance(result.ui_state, UIState)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            result.ui_state.micro_stats = MicroStatsState.zero_state()  # type: ignore

    def test_to_dict_has_agent_g_path(self):
        assembler = PayloadAssemblerV2()
        result = assembler.assemble(_MockDecision(), _MockSnapshot(), None, ())
        d = result.to_dict()
        assert "agent_g" in d
        assert "data" in d["agent_g"]
        assert "ui_state" in d["agent_g"]["data"]

    def test_atm_passthrough(self):
        assembler = PayloadAssemblerV2()
        atm = {"anchor_strike": 560.0, "current_iv": 0.12}
        result = assembler.assemble(_MockDecision(), _MockSnapshot(), atm, ())
        assert result.atm == atm

    def test_with_broadcast_fields_new_frozen(self):
        assembler = PayloadAssemblerV2()
        result = assembler.assemble(_MockDecision(), _MockSnapshot(), None, ())
        hb = "2026-03-04T09:30:00+00:00"
        updated = result.with_broadcast_fields(heartbeat_timestamp=hb, is_stale=False)
        assert updated.heartbeat_timestamp == hb
        # Original unchanged
        assert result.heartbeat_timestamp == ""

    def test_data_timestamp_prefers_l0_source_timestamp_typed_snapshot(self):
        assembler = PayloadAssemblerV2()
        snap = _MockSnapshot()
        snap.extra_metadata = {"source_data_timestamp_utc": "2026-03-06T14:30:00+00:00"}
        decision = _MockDecision()
        decision.computed_at = datetime(2026, 3, 6, 14, 30, 1, tzinfo=timezone.utc)

        result = assembler.assemble(decision, snap, None, ())
        assert result.data_timestamp == "2026-03-06T14:30:00+00:00"
        assert result.drift_ms == pytest.approx(1000.0, rel=0, abs=1e-6)
        assert result.drift_warning is True

    def test_data_timestamp_prefers_l0_source_timestamp_dict_snapshot(self):
        assembler = PayloadAssemblerV2()
        decision = _MockDecision()
        decision.computed_at = datetime(2026, 3, 6, 14, 31, 0, tzinfo=timezone.utc)
        snapshot = {"spot": 562.5, "chain": [], "as_of_utc": "2026-03-06T14:30:00+00:00"}

        result = assembler.assemble(decision, snapshot, None, ())
        assert result.data_timestamp == "2026-03-06T14:30:00+00:00"
        assert result.drift_ms == pytest.approx(60000.0, rel=0, abs=1e-6)

    def test_data_timestamp_falls_back_to_computed_at_when_source_invalid(self):
        assembler = PayloadAssemblerV2()
        snap = _MockSnapshot()
        snap.extra_metadata = {"source_data_timestamp_utc": "bad-timestamp"}
        decision = _MockDecision()
        decision.computed_at = datetime(2026, 3, 6, 14, 30, 1, tzinfo=timezone.utc)

        result = assembler.assemble(decision, snap, None, ())
        assert result.data_timestamp == decision.computed_at.isoformat()
        assert result.drift_ms == 0.0
        assert result.drift_warning is False


# ─────────────────────────────────────────────────────────────────────────────
# FieldDeltaEncoder tests
# ─────────────────────────────────────────────────────────────────────────────

class TestFieldDeltaEncoder:
    def test_first_encode_is_full(self):
        enc = FieldDeltaEncoder(full_snapshot_interval=999.0)
        p = _make_frozen(version=1)
        msg = enc.encode(p, heartbeat_timestamp="t")
        assert msg.type == DeltaType.FULL
        assert msg.data is not None

    def test_second_encode_is_delta(self):
        enc = FieldDeltaEncoder(full_snapshot_interval=999.0)
        p1 = _make_frozen(version=1, spot=560.0)
        p2 = _make_frozen(version=2, spot=561.0)
        enc.encode(p1, "t1")
        msg2 = enc.encode(p2, "t2")
        assert msg2.type == DeltaType.DELTA

    def test_force_full(self):
        enc = FieldDeltaEncoder(full_snapshot_interval=999.0)
        p1 = _make_frozen(version=1)
        p2 = _make_frozen(version=2)
        enc.encode(p1, "t1")
        msg2 = enc.encode(p2, "t2", force_full=True)
        assert msg2.type == DeltaType.FULL

    def test_delta_has_changes(self):
        enc = FieldDeltaEncoder(full_snapshot_interval=999.0)
        p1 = _make_frozen(version=1, spot=560.0)
        p2 = _make_frozen(version=2, spot=565.0)
        enc.encode(p1, "t1")
        msg2 = enc.encode(p2, "t2")
        assert msg2.changes is not None
        assert "spot" in msg2.changes
        assert msg2.changes["spot"] == 565.0

    def test_delta_ratio(self):
        enc = FieldDeltaEncoder(full_snapshot_interval=999.0)
        for i in range(5):
            enc.encode(_make_frozen(version=i), f"t{i}")
        # First is full, rest 4 are delta → ratio = 4/5 = 0.8
        assert abs(enc.delta_ratio - 0.8) < 1e-9

    def test_is_stale_propagated(self):
        enc = FieldDeltaEncoder(full_snapshot_interval=999.0)
        p = _make_frozen()
        msg = enc.encode(p, "t", is_stale=True)
        # Full message: spot should be in data
        assert msg.data is not None

    def test_to_dict_full_has_spotkey(self):
        enc = FieldDeltaEncoder()
        msg = enc.encode(_make_frozen(spot=572.0), "t")
        d = msg.to_dict()
        assert d.get("spot") == 572.0


# ─────────────────────────────────────────────────────────────────────────────
# TimeSeriesStoreV2 tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTimeSeriesStoreV2:
    def test_write_and_get_latest_sync(self):
        store = TimeSeriesStoreV2(max_hot=10)
        p = _make_frozen(version=1)
        asyncio.run(store.write(p))
        result = store.get_latest(1)
        assert len(result) == 1
        assert result[0].version == 1

    def test_ring_buffer_overflow(self):
        store = TimeSeriesStoreV2(max_hot=5)
        for i in range(10):
            asyncio.run(store.write(_make_frozen(version=i)))
        # Hot layer should only hold 5 newest
        assert store.hot_size() == 5
        latest = store.get_latest(5)
        versions = [p.version for p in latest]
        assert max(versions) == 9

    def test_get_latest_single(self):
        store = TimeSeriesStoreV2(max_hot=10)
        for i in range(3):
            asyncio.run(store.write(_make_frozen(version=i)))
        latest = store.get_latest_single()
        assert latest is not None
        assert latest.version == 2

    def test_get_latest_empty_returns_empty(self):
        store = TimeSeriesStoreV2()
        assert store.get_latest(5) == []
        assert store.get_latest_single() is None

    def test_hot_size_increments(self):
        store = TimeSeriesStoreV2(max_hot=100)
        for i in range(7):
            asyncio.run(store.write(_make_frozen(version=i)))
        assert store.hot_size() == 7

    def test_diagnostics_schema(self):
        store = TimeSeriesStoreV2()
        d = store.get_diagnostics()
        assert "hot_size" in d
        assert "total_writes" in d
        assert "warm_writes" in d
        assert "warm_failures" in d

    def test_get_warm_latest_fallback_to_hot(self):
        """Without Redis, get_warm_latest falls back to hot layer."""
        store = TimeSeriesStoreV2(max_hot=10, redis=None)
        for i in range(3):
            asyncio.run(store.write(_make_frozen(version=i, spot=float(560+i))))
        result = asyncio.run(store.get_warm_latest(count=3))
        assert isinstance(result, list)
        # Should have 3 entries from hot layer
        assert len(result) == 3

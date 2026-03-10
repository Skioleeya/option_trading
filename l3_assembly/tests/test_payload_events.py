"""Tests for L3 payload_events and delta_events contracts.

Phase 1 test suite: 20 tests covering:
- MetricCard validation
- MicroStatsState construction and serialization
- UIState immutability and to_dict() schema
- FrozenPayload serialization (legacy schema alignment)
- DeltaPayload validation
"""
import dataclasses
import pytest
from datetime import datetime, timezone

from l3_assembly.events.payload_events import (
    MetricCard,
    MicroStatsState,
    TacticalTriadState,
    WallMigrationRow,
    DepthProfileRow,
    MTFFlowState,
    ActiveOptionRow,
    UIState,
    SignalData,
    FrozenPayload,
    VALID_BADGE_TOKENS,
)
from l3_assembly.events.delta_events import DeltaPayload, DeltaType


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _metric_card(badge: str = "badge-neutral") -> MetricCard:
    return MetricCard(label="—", badge=badge)


def _micro_stats(badge: str = "badge-neutral") -> MicroStatsState:
    card = _metric_card(badge)
    return MicroStatsState(net_gex=card, wall_dyn=card, vanna=card, momentum=card)


def _signal_data() -> SignalData:
    return SignalData(
        direction="NEUTRAL",
        confidence=0.55,
        pre_guard_direction="NEUTRAL",
        guard_actions=(),
        signal_summary={"atm_iv": "0.12"},
        fusion_weights={"momentum": 0.4, "trap": 0.3},
        latency_ms=8.5,
        version=42,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )


def _ui_state() -> UIState:
    return UIState(
        micro_stats=MicroStatsState.zero_state(),
        tactical_triad=TacticalTriadState.zero_state(),
        wall_migration=(),
        depth_profile=(),
        active_options=(),
        mtf_flow=MTFFlowState.zero_state(),
        skew_dynamics={},
        macro_volume_map={},
    )


def _frozen_payload() -> FrozenPayload:
    return FrozenPayload(
        data_timestamp="2026-03-04T09:30:00+00:00",
        broadcast_timestamp="2026-03-04T09:30:00+00:00",
        spot=560.25,
        version=42,
        drift_ms=12.5,
        drift_warning=False,
        signal=_signal_data(),
        ui_state=_ui_state(),
        atm=None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# MetricCard tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMetricCard:
    def test_valid_badges(self):
        for badge in sorted(VALID_BADGE_TOKENS):
            mc = MetricCard(label="test", badge=badge)
            assert mc.badge == badge

    def test_invalid_badge_raises(self):
        with pytest.raises(ValueError, match="badge-invalid"):
            MetricCard(label="x", badge="badge-invalid")

    def test_frozen(self):
        mc = MetricCard(label="x", badge="badge-neutral")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            mc.label = "y"  # type: ignore

    def test_to_dict_no_tooltip(self):
        mc = MetricCard(label="482B", badge="badge-red")
        d = mc.to_dict()
        assert d == {"label": "482B", "badge": "badge-red"}
        assert "tooltip" not in d

    def test_to_dict_with_tooltip(self):
        mc = MetricCard(label="482B", badge="badge-red", tooltip="Net GEX")
        d = mc.to_dict()
        assert d["tooltip"] == "Net GEX"


# ─────────────────────────────────────────────────────────────────────────────
# MicroStatsState tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMicroStatsState:
    def test_construction(self):
        ms = _micro_stats()
        assert ms.net_gex.label == "—"

    def test_frozen(self):
        ms = _micro_stats()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            ms.net_gex = MetricCard(label="x", badge="badge-neutral")  # type: ignore

    def test_to_dict_keys(self):
        d = _micro_stats().to_dict()
        assert set(d.keys()) == {"net_gex", "wall_dyn", "vanna", "momentum"}

    def test_zero_state(self):
        z = MicroStatsState.zero_state()
        assert z.net_gex.label == "—"
        assert z.net_gex.badge == "badge-neutral"

    def test_to_dict_schema(self):
        d = _micro_stats("badge-red").to_dict()
        assert d["net_gex"]["badge"] == "badge-red"
        assert "label" in d["wall_dyn"]


# ─────────────────────────────────────────────────────────────────────────────
# DepthProfileRow tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDepthProfileRow:
    def test_valid(self):
        row = DepthProfileRow(
            strike=560.0,
            call_pct=0.75,
            put_pct=0.25,
            is_spot=True,
            is_flip=False,
            is_dominant_put=False,
            is_dominant_call=True,
        )
        assert row.strike == 560.0

    def test_nan_call_gex_raises(self):
        import math
        with pytest.raises(ValueError, match="finite"):
            DepthProfileRow(
                strike=560.0,
                call_pct=float("nan"),
                put_pct=0.0,
                is_spot=False,
                is_flip=False,
                is_dominant_put=False,
                is_dominant_call=False,
            )

    def test_inf_put_gex_raises(self):
        with pytest.raises(ValueError, match="finite"):
            DepthProfileRow(
                strike=560.0,
                call_pct=0.0,
                put_pct=float("inf"),
                is_spot=False,
                is_flip=False,
                is_dominant_put=False,
                is_dominant_call=False,
            )

    def test_to_dict_keys(self):
        row = DepthProfileRow(
            strike=560.0,
            call_pct=0.75,
            put_pct=0.25,
            is_spot=True,
            is_flip=False,
            is_dominant_put=False,
            is_dominant_call=True,
        )
        d = row.to_dict()
        assert set(d.keys()) == {
            "strike",
            "call_pct",
            "put_pct",
            "is_spot",
            "is_flip",
            "is_dominant_put",
            "is_dominant_call",
        }


class TestActiveOptionRow:
    def test_to_dict_includes_placeholder_contract_fields(self):
        row = ActiveOptionRow(
            symbol="SPY",
            option_type="CALL",
            strike=560.0,
            implied_volatility=0.2,
            volume=1000,
            turnover=100000.0,
            flow=1200.0,
            flow_score=-0.8,
            impact_index=12.3,
            is_sweep=False,
            flow_deg_formatted="$1.2K",
            flow_volume_label="1K",
            flow_color="text-accent-red",
            flow_glow="",
            flow_intensity="LOW",
            flow_direction="BULLISH",
            flow_d_z=0.1,
            flow_e_z=0.2,
            flow_g_z=0.3,
            is_placeholder=True,
            slot_index=4,
        )
        payload = row.to_dict()
        assert payload["is_placeholder"] is True
        assert payload["slot_index"] == 4


# ─────────────────────────────────────────────────────────────────────────────
# UIState tests
# ─────────────────────────────────────────────────────────────────────────────

class TestUIState:
    def test_zero_state(self):
        z = UIState.zero_state()
        assert z.micro_stats.net_gex.label == "—"
        assert z.wall_migration == ()
        assert z.depth_profile == ()

    def test_wall_migration_is_tuple(self):
        z = UIState.zero_state()
        assert isinstance(z.wall_migration, tuple)

    def test_to_dict_keys(self):
        d = UIState.zero_state().to_dict()
        expected = {"micro_stats", "tactical_triad", "wall_migration",
                    "depth_profile", "active_options", "mtf_flow",
                    "skew_dynamics", "macro_volume_map", "iv_velocity"}
        assert set(d.keys()) == expected

    def test_frozen(self):
        z = UIState.zero_state()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            z.micro_stats = MicroStatsState.zero_state()  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# SignalData tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSignalData:
    def test_valid_directions(self):
        for d in ("BULLISH", "BEARISH", "NEUTRAL", "HALT"):
            sd = _signal_data()
            sd2 = dataclasses.replace(sd, direction=d)
            assert sd2.direction == d

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError):
            SignalData(
                direction="UNKNOWN", confidence=0.5,
                pre_guard_direction="NEUTRAL", guard_actions=(),
                signal_summary={}, fusion_weights={}, latency_ms=0.0,
                version=0, computed_at="2026-01-01T00:00:00",
            )

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValueError):
            SignalData(
                direction="NEUTRAL", confidence=1.5,
                pre_guard_direction="NEUTRAL", guard_actions=(),
                signal_summary={}, fusion_weights={}, latency_ms=0.0,
                version=0, computed_at="2026-01-01T00:00:00",
            )

    def test_neutral_factory(self):
        sd = SignalData.neutral()
        assert sd.direction == "NEUTRAL"
        assert sd.confidence == 0.0

    def test_to_dict_schema(self):
        d = _signal_data().to_dict()
        assert "direction" in d
        assert "confidence" in d
        assert "guard_actions" in d
        assert isinstance(d["guard_actions"], list)


# ─────────────────────────────────────────────────────────────────────────────
# FrozenPayload tests
# ─────────────────────────────────────────────────────────────────────────────

class TestFrozenPayload:
    def test_frozen(self):
        p = _frozen_payload()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            p.spot = 999.0  # type: ignore

    def test_to_dict_has_agent_g(self):
        """Frontend reads agent_g.data.* — must be present."""
        d = _frozen_payload().to_dict()
        assert "agent_g" in d
        assert "data" in d["agent_g"]
        assert "ui_state" in d["agent_g"]["data"]

    def test_to_dict_top_level_keys(self):
        d = _frozen_payload().to_dict()
        assert "type" in d
        assert "spot" in d
        assert "drift_ms" in d
        assert "timestamp" in d           # legacy alias

    def test_with_broadcast_fields(self):
        p = _frozen_payload()
        p2 = p.with_broadcast_fields(
            heartbeat_timestamp="2026-03-04T09:30:01",
            is_stale=False,
            msg_type="dashboard_update",
        )
        assert p2.heartbeat_timestamp == "2026-03-04T09:30:01"
        assert p2.is_stale is False
        # Original unchanged
        assert p.heartbeat_timestamp == ""

    def test_spot_in_to_dict(self):
        p = _frozen_payload()
        d = p.to_dict()
        assert d["spot"] == 560.25


# ─────────────────────────────────────────────────────────────────────────────
# DeltaPayload tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDeltaPayload:
    def test_full_requires_data(self):
        with pytest.raises(ValueError, match="FULL"):
            DeltaPayload(type=DeltaType.FULL, version=1,
                         timestamp="t", heartbeat_timestamp="t",
                         data=None)

    def test_delta_requires_changes_or_patch(self):
        with pytest.raises(ValueError, match="DELTA"):
            DeltaPayload(type=DeltaType.DELTA, version=2,
                         timestamp="t", heartbeat_timestamp="t",
                         prev_version=1)

    def test_full_to_dict_includes_type(self):
        dp = DeltaPayload(
            type=DeltaType.FULL, version=1,
            timestamp="t", heartbeat_timestamp="ht",
            data={"spot": 560.0},
        )
        d = dp.to_dict()
        assert d["type"] == "dashboard_update"
        assert d["spot"] == 560.0

    def test_delta_with_patch_to_dict(self):
        dp = DeltaPayload(
            type=DeltaType.DELTA, version=2, prev_version=1,
            timestamp="t", heartbeat_timestamp="ht",
            patch=[{"op": "replace", "path": "/spot", "value": 561.0}],
        )
        d = dp.to_dict()
        assert d["type"] == "dashboard_delta"
        assert d["patch"][0]["op"] == "replace"

    def test_delta_with_field_changes(self):
        dp = DeltaPayload(
            type=DeltaType.DELTA, version=3, prev_version=2,
            timestamp="t", heartbeat_timestamp="ht",
            changes={"spot": 562.0, "drift_ms": 5.0},
        )
        d = dp.to_dict()
        assert "changes" in d
        assert d["changes"]["spot"] == 562.0

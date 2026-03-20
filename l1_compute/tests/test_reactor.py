"""Tests for EnrichedSnapshot, L1Instrumentation, and L1 Compute Reactor.

Validates:
    1. EnrichedSnapshot is truly immutable (frozen dataclass)
    2. to_legacy_dict() contains all expected keys
    3. L1Instrumentation is safe to call with no OTel/Prometheus installed
    4. L1ComputeReactor.compute() returns valid EnrichedSnapshot end-to-end
    5. Reactor handles empty chain without crash
    6. Reactor SABR recalibration interval respected
"""

from __future__ import annotations

import asyncio
import math
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pytest

sys.path.insert(0, "e:\\US.market\\Option_v3")

from l1_compute.output.enriched_snapshot import (
    AggregateGreeks,
    ComputeQualityReport,
    EnrichedSnapshot,
    MicroSignals,
)
from l1_compute.observability.l1_instrumentation import L1Instrumentation
from l1_compute.reactor import L1ComputeReactor
from l1_compute.microstructure.wall_context_builder import build_wall_context

_ET = ZoneInfo("US/Eastern")


# ─────────────────────────────────────────────────────────────────────────────
# EnrichedSnapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestEnrichedSnapshot:

    def _make_snap(self) -> EnrichedSnapshot:
        now = datetime.now(_ET)
        return EnrichedSnapshot(
            spot=560.0,
            chain=None,
            aggregates=AggregateGreeks(
                net_gex=1.5, atm_iv=0.20, call_wall=565.0, put_wall=555.0, flip_level=560.0
            ),
            microstructure=MicroSignals(vpin_composite=0.30),
            quality=ComputeQualityReport(compute_tier="numpy", contracts_computed=100),
            ttm_seconds=10000.0,
            version=42,
            computed_at=now,
        )

    def test_immutable_frozen(self):
        snap = self._make_snap()
        with pytest.raises((AttributeError, TypeError)):
            snap.spot = 999.0  # type: ignore

    def test_property_accessors(self):
        snap = self._make_snap()
        assert snap.atm_iv == 0.20
        assert snap.net_gex == 1.5
        assert snap.call_wall == 565.0
        assert snap.put_wall == 555.0
        assert snap.flip_level == 560.0

    def test_to_legacy_dict_keys(self):
        snap = self._make_snap()
        d = snap.to_legacy_dict()
        required_keys = [
            "net_gex", "net_vanna_raw_sum", "net_vanna", "net_charm_raw_sum", "net_charm", "call_wall", "put_wall",
            "flip_level", "flip_level_cumulative", "zero_gamma_level",
            "atm_iv", "spy_atm_iv", "vpin_score",
            "bbo_imbalance", "vol_accel_ratio", "ttm_seconds", "version",
        ]
        for k in required_keys:
            assert k in d, f"Missing key in legacy dict: {k}"

    def test_version_preserved(self):
        snap = self._make_snap()
        assert snap.version == 42

    def test_aggregate_greeks_frozen(self):
        agg = AggregateGreeks(net_gex=1.5)
        with pytest.raises((AttributeError, TypeError)):
            agg.net_gex = 0.0  # type: ignore

    def test_micro_signals_frozen(self):
        micro = MicroSignals(vpin_1m=0.5)
        with pytest.raises((AttributeError, TypeError)):
            micro.vpin_1m = 0.0  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# L1Instrumentation
# ─────────────────────────────────────────────────────────────────────────────

class TestL1Instrumentation:

    def test_no_errors_without_otel(self):
        """All instrumentation methods must be safe with no OTel installed."""
        inst = L1Instrumentation()
        with inst.span_compute():
            with inst.span_iv_resolution():
                pass
            with inst.span_greeks_kernel() as span:
                span.set_attribute("tier", "numpy")
        # No exception = pass

    def test_metrics_safe_without_prometheus(self):
        inst = L1Instrumentation()
        inst.record_greeks_latency(0.005)
        inst.record_compute_tier("numpy")
        inst.record_iv_source("ws", 50)
        inst.record_contracts_computed(100)
        inst.record_nan_count(0)
        inst.set_chain_size(200)


# ─────────────────────────────────────────────────────────────────────────────
# L1 Compute Reactor
# ─────────────────────────────────────────────────────────────────────────────

def _make_chain_entries(n: int, spot: float = 560.0) -> list[dict]:
    """Synthetic option chain for reactor integration test."""
    entries = []
    for i in range(n):
        strike = spot - 5 + (i * 0.5)
        opt_type = "CALL" if i % 2 == 0 else "PUT"
        entries.append({
            "symbol":              f"SPY{i:04d}",
            "strike":              strike,
            "type":                opt_type,
            "implied_volatility":  0.18 + (i * 0.001),
            "iv_timestamp":        0.0,  # no WS timestamp → chain path
            "open_interest":       int(1000 + i * 100),
            "contract_multiplier": 100,
            "volume":              50 + i,
        })
    return entries


class TestL1ComputeReactor:

    @pytest.mark.asyncio
    async def test_basic_compute_returns_snapshot(self):
        """Reactor must return EnrichedSnapshot with valid spot and version."""
        reactor = L1ComputeReactor(sabr_enabled=False)
        chain = _make_chain_entries(50)
        snap = await reactor.compute(chain, spot=560.0, l0_version=7)
        assert isinstance(snap, EnrichedSnapshot)
        assert snap.spot == 560.0
        assert snap.version == 7

    @pytest.mark.asyncio
    async def test_empty_chain_returns_empty_snapshot(self):
        reactor = L1ComputeReactor(sabr_enabled=False)
        snap = await reactor.compute([], spot=560.0, l0_version=1)
        assert isinstance(snap, EnrichedSnapshot)
        assert snap.quality.contracts_computed == 0

    @pytest.mark.asyncio
    async def test_empty_chain_preserves_extra_metadata(self):
        reactor = L1ComputeReactor(sabr_enabled=False)
        metadata = {
            "rust_active": False,
            "shm_stats": {"status": "UNINITIALIZED", "head": 0, "tail": 0},
            "source_data_timestamp_utc": None,
        }
        snap = await reactor.compute(
            [],
            spot=560.0,
            l0_version=2,
            extra_metadata=metadata,
        )
        assert snap.extra_metadata == metadata

    @pytest.mark.asyncio
    async def test_nonpositive_spot_preserves_extra_metadata(self):
        reactor = L1ComputeReactor(sabr_enabled=False)
        metadata = {
            "rust_active": True,
            "shm_stats": {"status": "ERROR", "head": 0, "tail": 0},
            "source_data_timestamp_utc": "2026-03-17T18:00:00+00:00",
        }
        snap = await reactor.compute(
            _make_chain_entries(3),
            spot=0.0,
            l0_version=3,
            extra_metadata=metadata,
        )
        assert snap.extra_metadata == metadata

    @pytest.mark.asyncio
    async def test_all_iv_invalid_preserves_extra_metadata(self):
        reactor = L1ComputeReactor(sabr_enabled=False)
        metadata = {
            "rust_active": True,
            "shm_stats": {"status": "OK", "head": 5, "tail": 5},
            "source_data_timestamp_utc": "2026-03-17T18:01:00+00:00",
        }
        chain = [
            {
                "symbol": "SPY_BAD",
                "strike": 560.0,
                "type": "CALL",
                "implied_volatility": 0.0,
                "open_interest": 1000,
                "contract_multiplier": 100,
                "volume": 10,
            }
        ]
        snap = await reactor.compute(
            chain,
            spot=560.0,
            l0_version=4,
            extra_metadata=metadata,
        )
        assert snap.quality.contracts_computed == 0
        assert snap.extra_metadata == metadata

    @pytest.mark.asyncio
    async def test_snapshot_contracts_computed(self):
        reactor = L1ComputeReactor(sabr_enabled=False)
        chain = _make_chain_entries(100)
        snap = await reactor.compute(chain, spot=560.0, l0_version=99)
        # All entries have valid chain IV → all should compute
        assert snap.quality.contracts_computed == 100
        assert snap.quality.contracts_skipped == 0

    @pytest.mark.asyncio
    async def test_quality_report_compute_tier(self):
        """Compute tier in quality report must be a valid tier name."""
        reactor = L1ComputeReactor(sabr_enabled=False)
        chain = _make_chain_entries(50)
        snap = await reactor.compute(chain, spot=560.0)
        assert snap.quality.compute_tier in ("gpu", "gpu_only_blocked", "numba", "numpy")

    @pytest.mark.asyncio
    async def test_legacy_dict_output_compatible(self):
        """to_legacy_dict() should not raise and contain net_gex."""
        reactor = L1ComputeReactor(sabr_enabled=False)
        chain = _make_chain_entries(50)
        snap = await reactor.compute(chain, spot=560.0)
        d = snap.to_legacy_dict()
        assert "net_gex" in d
        assert "atm_iv" in d
        assert d["net_vanna_raw_sum"] == pytest.approx(d["net_vanna"])
        assert d["net_charm_raw_sum"] == pytest.approx(d["net_charm"])

    @pytest.mark.asyncio
    async def test_chain_includes_computed_gamma_and_vanna_columns(self):
        reactor = L1ComputeReactor(sabr_enabled=False)
        chain = _make_chain_entries(30)
        snap = await reactor.compute(chain, spot=560.0, l0_version=3)
        assert hasattr(snap.chain, "schema")
        names = set(snap.chain.schema.names)
        assert "computed_gamma" in names
        assert "computed_vanna" in names

    @pytest.mark.asyncio
    async def test_compute_audit_metadata_passthrough(self):
        reactor = L1ComputeReactor(sabr_enabled=False)
        chain = _make_chain_entries(20)
        audit = {
            "tick_id": 12,
            "snapshot_version": 88,
            "compute_id": 4,
            "gpu_task_id": "gpu-task-88-4",
        }
        snap = await reactor.compute(
            chain,
            spot=560.0,
            l0_version=88,
            extra_metadata={"compute_audit": audit},
        )
        assert snap.extra_metadata.get("compute_audit") == audit

    @pytest.mark.asyncio
    async def test_wall_context_emitted_for_l3_contract(self):
        reactor = L1ComputeReactor(sabr_enabled=False)
        chain = _make_chain_entries(40)
        snap = await reactor.compute(chain, spot=560.0, l0_version=21)

        assert isinstance(snap.microstructure.wall_context, dict)
        assert "gamma_regime" in snap.microstructure.wall_context
        assert "hedge_flow_intensity" in snap.microstructure.wall_context

        wall = snap.microstructure.wall_migration or {}
        assert isinstance(wall, dict)
        assert "wall_context" in wall

    @pytest.mark.asyncio
    async def test_microstructure_depth_update(self):
        """update_microstructure_depth should not crash."""
        reactor = L1ComputeReactor(sabr_enabled=False)

        class _Bid:
            volume = 500.0
        class _Ask:
            volume = 300.0

        reactor.update_microstructure_depth("SYM001", [_Bid()], [_Ask()])
        sig = reactor._bbo.get_signal("SYM001")
        assert sig is not None
        assert sig.raw_imbalance > 0  # bid heavier

    @pytest.mark.asyncio
    async def test_microstructure_trade_update(self):
        reactor = L1ComputeReactor(sabr_enabled=False)
        trades = [{"vol": 100.0, "dir": 1}] * 10  # all buys
        reactor.update_microstructure_trades("SYM001", trades)
        assert "SYM001" in reactor._vpin_map

    def test_sync_version(self):
        """_compute_sync must be callable synchronously (for thread pool test)."""
        reactor = L1ComputeReactor(sabr_enabled=False)
        chain = _make_chain_entries(20)
        result = reactor._compute_sync(chain, spot=560.0, l0_version=1, iv_cache={}, spot_at_sync={})
        assert isinstance(result, EnrichedSnapshot)

    def test_compute_sync_empty_chain_preserves_extra_metadata(self):
        reactor = L1ComputeReactor(sabr_enabled=False)
        metadata = {
            "rust_active": False,
            "shm_stats": {"status": "UNINITIALIZED", "head": 0, "tail": 0},
            "source_data_timestamp_utc": None,
        }
        snap = reactor._compute_sync(
            [],
            spot=560.0,
            l0_version=31,
            iv_cache={},
            spot_at_sync={},
            extra_metadata=metadata,
        )
        assert snap.extra_metadata == metadata

    def test_compute_sync_nonpositive_spot_preserves_extra_metadata(self):
        reactor = L1ComputeReactor(sabr_enabled=False)
        metadata = {
            "rust_active": True,
            "shm_stats": {"status": "ERROR", "head": 0, "tail": 0},
            "source_data_timestamp_utc": "2026-03-17T18:00:00+00:00",
        }
        snap = reactor._compute_sync(
            _make_chain_entries(3),
            spot=0.0,
            l0_version=32,
            iv_cache={},
            spot_at_sync={},
            extra_metadata=metadata,
        )
        assert snap.extra_metadata == metadata

    def test_compute_sync_all_iv_invalid_preserves_extra_metadata(self):
        reactor = L1ComputeReactor(sabr_enabled=False)
        metadata = {
            "rust_active": True,
            "shm_stats": {"status": "OK", "head": 5, "tail": 5},
            "source_data_timestamp_utc": "2026-03-17T18:01:00+00:00",
        }

        class _InvalidIV:
            is_valid = False
            value = 0.0

        class _IVStats:
            ws_hits = 0
            rest_hits = 0
            chain_hits = 0
            sabr_hits = 0
            misses = 1

        class _InvalidResolver:
            stats = _IVStats()

            def batch_resolve(self, chain_snapshot, spot, iv_cache, spot_at_sync, ttm_years=0.0):
                return {entry["symbol"]: _InvalidIV() for entry in chain_snapshot}

        reactor._iv_resolver = _InvalidResolver()  # type: ignore[assignment]
        snap = reactor._compute_sync(
            _make_chain_entries(1),
            spot=560.0,
            l0_version=33,
            iv_cache={},
            spot_at_sync={},
            extra_metadata=metadata,
        )
        assert snap.quality.contracts_computed == 0
        assert snap.extra_metadata == metadata

    def test_wall_context_uses_million_unit_without_double_scaling(self):
        chain = [
            {"strike": 554.0, "volume": 120},
            {"strike": 555.0, "volume": 360},
            {"strike": 560.0, "volume": 220},
            {"strike": 565.0, "volume": 340},
            {"strike": 566.0, "volume": 110},
        ]

        ctx = build_wall_context(
            chain,
            net_gex=-12.0,
            call_wall=565.0,
            put_wall=555.0,
            call_wall_gex=18.5,
            put_wall_gex=11.25,
        )

        expected_notional_m = abs(18.5) + abs(11.25)
        assert ctx["near_wall_hedge_notional_m"] == pytest.approx(expected_notional_m)
        assert math.isfinite(float(ctx["hedge_flow_intensity"]))
        assert math.isfinite(float(ctx["counterfactual_vol_impact_bps"]))

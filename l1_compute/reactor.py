"""L1 Compute Reactor — Main orchestrator for the L1 computation layer.

Replaces the per-tick BSM computation scattered across:
    - GreeksEngine.enrich()
    - GreeksExtractor.compute()
    - DepthEngine.get_flow_snapshot()

Execution flow:
    1. Read L0 MVCCChainStateStore snapshot (version-tagged, reads never block)
    2. IV Resolution — IVResolver batch resolves all symbols
    3. SABR Calibration — every 120s if enough calibration data available
    4. Compute Greeks — ComputeRouter selects GPU / Numba / NumPy
    5. StreamingAggregator — incremental GEX/Vanna/Charm update
    6. Microstructure — VPIN v2, BBO v2, VolAccel v2 composite
    7. Build EnrichedSnapshot (immutable) and return to caller

Threading model:
    - compute() is async and offloads heavy work to asyncio.to_thread()
    - Reactor holds no mutable state shared with event loop (safe re-entry)

Cutover:
    In option_chain_builder.py, replace GreeksEngine.enrich() call with:
        from l1_compute.reactor import L1ComputeReactor
        reactor = L1ComputeReactor(...)
        snapshot = await reactor.compute(chain_snapshot, spot, l0_version)
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from zoneinfo import ZoneInfo

import numpy as np
import pyarrow as pa

from l1_compute.arrow.schema import dicts_to_record_batch, ensure_record_batch

from l1_compute.aggregation.streaming_aggregator import AggregateGreeks, StreamingAggregator
from l1_compute.compute.compute_router import ComputeRouter, ComputeTier
from l1_compute.iv.iv_resolver import IVResolver, IVSource
from l1_compute.iv.sabr_calibrator import SABRCalibrator
from l1_compute.microstructure.bbo_v2 import BBOv2
from l1_compute.microstructure.vpin_v2 import VPINv2, VPINRegime
from l1_compute.microstructure.vol_accel_v2 import VolAccelV2
from l1_compute.observability.l1_instrumentation import L1Instrumentation
from l1_compute.output.enriched_snapshot import (
    AggregateGreeks as OutAggregateGreeks,
    ComputeQualityReport,
    EnrichedSnapshot,
    MicroSignals,
)
from l1_compute.time.ttm_v2 import SettlementType, get_trading_ttm_v2_scalar

# Refactor: Moving Agent B trackers to L1
from l1_compute.analysis.mtf_iv_engine import MTFIVEngine
from l1_compute.analysis.volume_imbalance_engine import VolumeImbalanceEngine
from l1_compute.analysis.jump_detector import JumpDetector
from l1_compute.trackers.iv_velocity_tracker import IVVelocityTracker
from l1_compute.trackers.vanna_flow_analyzer import VannaFlowAnalyzer
from l1_compute.trackers.wall_migration_tracker import WallMigrationTracker
from shared.config import settings

logger = logging.getLogger(__name__)

_ET = ZoneInfo("US/Eastern")
_SABR_RECALIBRATE_INTERVAL: float = 120.0   # seconds


class L1ComputeReactor:
    """Orchestrates the full L1 computation pipeline.

    Designed to be instantiated once at startup (alongside OptionChainBuilder)
    and called on every chain update tick.

    Args:
        r:            Risk-free rate (continuously compounded).
        q:            Dividend yield (continuously compounded).
        sabr_enabled: Enable SABR calibration (requires scipy).
        iv_ws_ttl:    WS IV time-to-live in seconds.
    """

    def __init__(
        self,
        r: float = 0.05,
        q: float = 0.0,
        sabr_enabled: bool = True,
        iv_ws_ttl: float = 7200.0,
    ) -> None:
        self._r = r
        self._q = q

        # Core components
        self._router     = ComputeRouter()
        self._aggregator = StreamingAggregator()
        self._iv_resolver = IVResolver(ws_ttl=iv_ws_ttl)
        self._sabr       = SABRCalibrator() if sabr_enabled else None
        self._inst       = L1Instrumentation()

        # Microstructure (per-symbol, created lazily)
        self._vpin_map:  dict[str, VPINv2] = {}
        self._bbo        = BBOv2()
        self._vol_accel  = VolAccelV2()

        # Integrated Trackers (Phase 1 Refactor)
        self._iv_tracker = IVVelocityTracker()
        self._wall_tracker = WallMigrationTracker()
        self._vanna_analyzer = VannaFlowAnalyzer()
        self._mtf_iv_engine = MTFIVEngine()
        self._vib_engine = VolumeImbalanceEngine()
        self._jump_detector = JumpDetector()

        # MTF intervals and buffers for VSRSD
        self._MTF_INTERVALS: dict[str, float] = {"1m": 60.0, "5m": 300.0, "15m": 900.0}
        self._mtf_buf: dict[str, list[float]] = {"1m": [], "5m": [], "15m": []}
        self._mtf_last_push: dict[str, float] = {"1m": 0.0, "5m": 0.0, "15m": 0.0}

        # SABR state
        self._last_sabr_at: float = 0.0

        logger.info(
            "[L1ComputeReactor] Initialized — GPU=%s SABR=%s",
            self._router.gpu_available,
            sabr_enabled,
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    async def compute(
        self,
        chain_snapshot: Union[List[dict[str, Any]], pa.RecordBatch],
        spot: float,
        l0_version: int = 0,
        iv_cache: Optional[dict[str, float]] = None,
        spot_at_sync: Optional[dict[str, float]] = None,
        extra_metadata: Optional[dict[str, Any]] = None,
    ) -> EnrichedSnapshot:
        """Execute the full L1 compute pipeline asynchronously.

        Args:
            chain_snapshot: List of option entry dicts from L0/ChainStateStore.
            spot:           Current underlying spot price.
            l0_version:     L0 MVCC version for provenance tracking.
            iv_cache:       REST IV baseline dict {symbol: iv}.
            spot_at_sync:   {symbol: spot_at_last_iv_sync}.

        Returns:
            Immutable EnrichedSnapshot ready for L2 Decision Layer.
        """
        if not chain_snapshot or spot <= 0:
            return self._empty_snapshot(l0_version)

        iv_cache     = iv_cache or {}
        spot_at_sync = spot_at_sync or {}

        with self._inst.span_compute():
            # Offload all CPU-intensive work to thread pool
            snapshot = await asyncio.to_thread(
                self._compute_sync,
                chain_snapshot,
                spot,
                l0_version,
                iv_cache,
                spot_at_sync,
                extra_metadata or {},
            )

        return snapshot

    def update_microstructure_depth(
        self,
        symbol: str,
        bids: list[Any],
        asks: list[Any],
    ) -> None:
        """Update BBO imbalance from a depth push event (call from asyncio loop).

        This is a fast, synchronous update — no thread offload needed.
        """
        self._bbo.update(symbol, bids, asks)

    def update_microstructure_trades(
        self,
        symbol: str,
        trades: list[dict],
    ) -> None:
        """Update VPIN from trade events for a specific symbol."""
        if symbol not in self._vpin_map:
            self._vpin_map[symbol] = VPINv2()
        self._vpin_map[symbol].update(trades)

    # ── Private synchronous pipeline ──────────────────────────────────────────

    def _compute_sync(
        self,
        chain_snapshot: Union[List[dict[str, Any]], pa.RecordBatch],
        spot: float,
        l0_version: int,
        iv_cache: dict[str, float],
        spot_at_sync: dict[str, float],
        extra_metadata: dict[str, Any],
    ) -> EnrichedSnapshot:
        """Full pipeline (runs in thread pool via asyncio.to_thread)."""
        t_start = time.monotonic()
        now = datetime.now(_ET)

        # Ensure data is pa.RecordBatch
        rb = ensure_record_batch(chain_snapshot)
        n = rb.num_rows
        self._inst.set_chain_size(n)

        if n == 0 or spot <= 0.0:
            logger.debug("[L1ComputeReactor] Skipping: snapshot empty or spot <= 0")
            return self._empty_snapshot(l0_version)

        # ── Step 1: IV Resolution ──────────────────────────────────────────────
        ttm_years = get_trading_ttm_v2_scalar(now)
        t_iv = time.monotonic()
        with self._inst.span_iv_resolution():
            resolved_ivs = self._iv_resolver.batch_resolve(
                chain_snapshot, spot, iv_cache, spot_at_sync, ttm_years=ttm_years
            )

        # ── Step 2: Conditionally recalibrate SABR ────────────────────────────
        if (self._sabr is not None and
                (time.monotonic() - self._last_sabr_at) >= _SABR_RECALIBRATE_INTERVAL):
            try:
                # We can fallback to dictionaries for SABR easily here as it uses fewer columns
                dicts_for_sabr = chain_snapshot if isinstance(chain_snapshot, list) else rb.to_pylist()
                self._sabr.calibrate_from_chain(dicts_for_sabr, forward=spot, ttm=ttm_years)
                self._last_sabr_at = time.monotonic()
            except Exception as exc:
                logger.debug("[L1ComputeReactor] SABR calibration skipped: %s", exc)

        # ── Step 3: Build arrays for batch compute ──────────────────────
        # Extract native Zero-Copy numpy arrays directly from the RecordBatch
        spots_arr   = np.full(n, spot, dtype=np.float64)
        strikes_arr = rb.column("strike").to_numpy()
        is_call_arr = rb.column("is_call").to_numpy(zero_copy_only=False)
        ois_arr     = rb.column("open_interest").to_numpy()
        mults_arr   = rb.column("contract_multiplier").to_numpy()
        
        # IV array logic needs to integrate with resolved_ivs
        # For now, fast path: use IV from RecordBatch if not replaced by WS/SABR lookup.
        # Alternatively, we patch the elements. To maintain existing logic:
        symbols    = rb.column("symbol").to_pylist()
        ivs_arr    = np.zeros(n, dtype=np.float64)
        iv_missing = 0
        valid_mask = np.zeros(n, dtype=np.bool_)
        
        for i, sym in enumerate(symbols):
            rv = resolved_ivs.get(sym)
            if rv is None or not rv.is_valid:
                iv_missing += 1
            else:
                ivs_arr[i] = rv.value
                valid_mask[i] = True

        n_valid = int(np.sum(valid_mask))
        iv_stats = self._iv_resolver.stats

        if n_valid == 0:
            logger.info("[L1ComputeReactor] compute bypassed: n_valid = 0 (Total n=%d)", n)
            return self._empty_snapshot(l0_version)

        # ── Step 4: Greeks batch compute ──────────────────────────────────────
        t_greeks = time.monotonic()

        with self._inst.span_greeks_kernel():
            matrix, decision = self._router.compute(
                spots_arr, strikes_arr, ivs_arr, ttm_years, is_call_arr,
                r=self._r, q=self._q, ois=ois_arr, mults=mults_arr,
            )
        greeks_ms = (time.monotonic() - t_greeks) * 1000.0
        self._inst.record_greeks_latency(greeks_ms / 1000.0)
        self._inst.record_compute_tier(decision.tier.value)

        # ── Step 5: Streaming Aggregation ──────────────────────────────────────
        t_agg = time.monotonic()
        with self._inst.span_aggregation():
            self._aggregator.full_recompute(
                matrix, strikes_arr, is_call_arr, symbols=symbols
            )
            agg = self._aggregator.snapshot()
        agg_ms = (time.monotonic() - t_agg) * 1000.0

        # ATM IV extraction
        atm_iv = self._extract_atm_iv(
            strikes_arr[valid_mask], ivs_arr[valid_mask], spot
        )

        # ── Extra Step: Populate Arrow Output ─────────────────────────────────
        # In a fully unified world we would append Greeks as Arrow columns. Keep original RB.
        out_batch = rb.append_column("computed_iv", pa.array(ivs_arr))
        out_batch = out_batch.append_column("gex", pa.array(matrix.gex_per_contract))

        # Split into call_gex / put_gex for legacy consumers
        out_batch = out_batch.append_column("call_gex", pa.array(matrix.call_gex))
        out_batch = out_batch.append_column("put_gex", pa.array(matrix.put_gex))

        # ── Step 6: Microstructure composite ──────────────────────────────────
        with self._inst.span_microstructure():
            micro_sig = self._build_micro_signals(
                chain_snapshot=chain_snapshot, 
                spot=spot, 
                now=now,
                atm_iv=atm_iv,
                net_gex=agg.net_gex,
                call_wall=agg.call_wall,
                put_wall=agg.put_wall
            )

        # ── Step 7: Quality report ─────────────────────────────────────────────
        nan_count = int(np.sum(~np.isfinite(matrix.delta)))
        self._inst.record_contracts_computed(n_valid)
        self._inst.record_nan_count(nan_count)
        self._inst.record_iv_source("ws",      iv_stats.ws_hits)
        self._inst.record_iv_source("rest",    iv_stats.rest_hits)
        self._inst.record_iv_source("chain",   iv_stats.chain_hits)
        self._inst.record_iv_source("sabr",    iv_stats.sabr_hits)
        self._inst.record_iv_source("missing", iv_stats.misses)

        quality = ComputeQualityReport(
            contracts_computed=n_valid,
            contracts_skipped=n - n_valid,
            nan_count=nan_count,
            compute_tier=decision.tier.value,
            greeks_latency_ms=greeks_ms,
            aggregation_latency_ms=agg_ms,
            iv_ws_count=iv_stats.ws_hits,
            iv_rest_count=iv_stats.rest_hits,
            iv_chain_count=iv_stats.chain_hits,
            iv_sabr_count=iv_stats.sabr_hits,
            iv_missing_count=iv_stats.misses,
            sabr_calibrated=self._sabr.is_calibrated if self._sabr else False,
            sabr_rmse=self._sabr.params.calibration_error
                      if (self._sabr and self._sabr.params) else 0.0,
        )

        # ── Assemble EnrichedSnapshot ──────────────────────────────────────────
        out_agg = OutAggregateGreeks(
            net_gex=agg.net_gex,
            net_vanna=agg.net_vanna,
            net_charm=agg.net_charm,
            call_wall=agg.call_wall,
            call_wall_gex=agg.call_wall_gex,
            put_wall=agg.put_wall,
            put_wall_gex=agg.put_wall_gex,
            flip_level=agg.flip_level,
            atm_iv=atm_iv,
            total_call_gex=agg.total_call_gex,
            total_put_gex=agg.total_put_gex,
            num_contracts=n_valid,
            per_strike_gex=agg.per_strike_gex,
        )

        ttm_seconds = ttm_years * 252.0 * 6.5 * 3600.0

        total_ms = (time.monotonic() - t_start) * 1000.0
        logger.info(
            "[L1ComputeReactor] compute n=%d tier=%s t=%.1fms gex=%.2f",
            n_valid, decision.tier.value, total_ms, agg.net_gex,
        )

        return EnrichedSnapshot(
            spot=spot,
            chain=out_batch,
            aggregates=out_agg,
            microstructure=micro_sig,
            quality=quality,
            ttm_seconds=ttm_seconds,
            version=l0_version,
            computed_at=now,
            extra_metadata=extra_metadata,
        )

    def _build_micro_signals(
        self,
        chain_snapshot: Union[list[dict], pa.RecordBatch],
        spot: float,
        now: datetime,
        atm_iv: float,
        net_gex: float,
        call_wall: float,
        put_wall: float,
    ) -> MicroSignals:
        """Assemble microstructure signals from VPIN, BBO, VolAccel, and trackers."""
        sim_clock_mono = time.monotonic()
        
        # 1. Base Signals (VPIN, BBO, VolAccel)
        all_vpin_scores = []
        for sym, vpin in self._vpin_map.items():
            sig = vpin.get_signal()
            all_vpin_scores.append(sig.composite_score)

        composite_vpin = (sum(all_vpin_scores) / len(all_vpin_scores)
                          if all_vpin_scores else 0.0)

        first_vpin = list(self._vpin_map.values())[0].get_signal() if self._vpin_map else None

        bbo_snap = self._bbo.get_all_snapshot()
        if bbo_snap:
            avg_imbalance = sum(s.raw_imbalance for s in bbo_snap.values()) / len(bbo_snap)
            avg_ewma_fast = sum(s.ewma_fast for s in bbo_snap.values()) / len(bbo_snap)
            avg_ewma_slow = sum(s.ewma_slow for s in bbo_snap.values()) / len(bbo_snap)
            avg_persist   = sum(s.persistence for s in bbo_snap.values()) / len(bbo_snap)
        else:
            avg_imbalance = avg_ewma_fast = avg_ewma_slow = avg_persist = 0.0

        phase = self._vol_accel.classify_phase(now.hour, now.minute)
        if isinstance(chain_snapshot, pa.RecordBatch):
            total_vol = float(np.sum(chain_snapshot.column("volume").to_numpy()))
            entries = chain_snapshot.to_pylist()
        else:
            total_vol = sum(float(e.get("volume", 0)) for e in chain_snapshot)
            entries = chain_snapshot
            
        va_sig = self._vol_accel.update_from_cumulative(total_vol, phase)
        regime = (first_vpin.tf_1m.regime if first_vpin else VPINRegime.NORMAL)

        # 2. Advanced Trackers (Phased Migration from Agent B)
        # 2a. Vanna Flow
        vanna_result = self._vanna_analyzer.update(
            spot=spot,
            atm_iv=atm_iv,
            net_gex=net_gex,
            spy_atm_iv=atm_iv,
            sim_clock_mono=sim_clock_mono,
        )
        wall_mult = vanna_result.wall_displacement_multiplier if vanna_result else 1.0

        # 2b. Wall Migration
        wall_result = self._wall_tracker.update(
            call_wall=call_wall,
            put_wall=put_wall,
            spot=spot,
            call_wall_volume=0, # Placeholder for now as it needs strike-specific volume
            put_wall_volume=0,
            sim_clock_mono=sim_clock_mono,
            displacement_multiplier=wall_mult,
        )

        # 2c. IV Velocity & MTF Engine
        iv_result = self._iv_tracker.update(
            spot=spot, atm_iv=atm_iv, sim_clock_mono=sim_clock_mono
        )
        if atm_iv > 0:
            for tf, interval in self._MTF_INTERVALS.items():
                self._mtf_buf[tf].append(atm_iv)
                if (sim_clock_mono - self._mtf_last_push[tf]) >= interval:
                    bar_mean = sum(self._mtf_buf[tf]) / len(self._mtf_buf[tf])
                    self._mtf_iv_engine.update(tf, bar_mean)
                    self._mtf_buf[tf].clear()
                    self._mtf_last_push[tf] = sim_clock_mono

        mtf_consensus = self._mtf_iv_engine.compute({
            "1m":  atm_iv, "5m":  atm_iv, "15m": atm_iv,
        })

        # 2d. Volume Imbalance & Jump Detection
        vib_result = self._vib_engine.update(
            entries, 
            spot,
            otm_call_vol=0, # These would ideally be pre-calculated in aggregation
            otm_put_vol=0,
            current_cumulative_total_chain_vol=int(total_vol),
        )
        jump_result = self._jump_detector.update(spot)

        # 2e. Squeeze Logic
        vol_accel_val = vib_result.vol_accel_ratio if vib_result else 1.0
        dealer_squeeze_alert = (
            vol_accel_val >= settings.vol_accel_squeeze_threshold
            and net_gex < 0
        )

        return MicroSignals(
            vpin_1m=first_vpin.tf_1m.score if first_vpin else 0.0,
            vpin_5m=first_vpin.tf_5m.score if first_vpin else 0.0,
            vpin_15m=first_vpin.tf_15m.score if first_vpin else 0.0,
            vpin_composite=composite_vpin,
            vpin_regime=regime.value,
            bbo_imbalance_raw=avg_imbalance,
            bbo_ewma_fast=avg_ewma_fast,
            bbo_ewma_slow=avg_ewma_slow,
            bbo_persistence=avg_persist,
            vol_accel_ratio=va_sig.ratio,
            vol_accel_threshold=va_sig.threshold,
            vol_accel_elevated=va_sig.is_elevated,
            vol_entropy=va_sig.entropy,
            session_phase=phase.value,
            # Tracker Results
            iv_velocity=iv_result.model_dump() if iv_result else None,
            mtf_consensus=mtf_consensus,
            iv_confidence=self._iv_tracker.get_confidence(),
            wall_migration=wall_result.model_dump() if wall_result else None,
            wall_confidence=self._wall_tracker.get_confidence(),
            vanna_flow_result=vanna_result.model_dump() if vanna_result else None,
            vanna_confidence=self._vanna_analyzer.get_confidence(),
            volume_imbalance=vib_result.model_dump() if vib_result else None,
            jump_detection=jump_result.model_dump() if jump_result else None,
            dealer_squeeze_alert=dealer_squeeze_alert,
            avg_atm_vpin_score=0.0,
        )

    @staticmethod
    def _extract_atm_iv(
        strikes: np.ndarray,
        ivs: np.ndarray,
        spot: float,
    ) -> float:
        """Extract IV of the option closest to ATM."""
        if len(strikes) == 0:
            return 0.0
        diffs = np.abs(strikes - spot)
        idx_atm = int(np.argmin(diffs))
        return float(ivs[idx_atm]) if ivs[idx_atm] > 0 else 0.0

    def _empty_snapshot(self, l0_version: int) -> EnrichedSnapshot:
        now = datetime.now(_ET)
        return EnrichedSnapshot(
            spot=0.0,
            chain=None,
            aggregates=OutAggregateGreeks(),
            microstructure=MicroSignals(),
            quality=ComputeQualityReport(),
            ttm_seconds=0.0,
            version=l0_version,
            computed_at=now,
            extra_metadata={},
        )

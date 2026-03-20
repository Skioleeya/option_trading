"""L1 Compute Reactor — thin orchestrator for the L1 computation pipeline.

Execution flow:
    1. Normalise L0 snapshot → Arrow RecordBatch (zero-copy)
    2. IV Resolution — IVResolver batch resolves all symbols
    3. SABR Calibration — every 120s when calibration data available
    4. Greeks batch compute — ComputeRouter selects GPU / Numba / NumPy
    5. StreamingAggregator — incremental GEX/Vanna/Charm update
    6. MicroSignalBuilder — delegates microstructure + tracker assembly
    7. Build EnrichedSnapshot (immutable) and return to caller

Threading model:
    - compute() is async; heavy work offloaded to asyncio.to_thread()
    - Reactor holds no mutable state shared with event loop (safe re-entry)

Dependencies for microstructure assembly are injected into MicroSignalBuilder
via constructor — reactor owns lifecycle, builder owns coordination logic.
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
from l1_compute.microstructure.micro_signal_builder import MicroSignalBuilder
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

# Tracker imports (Phase 1 Refactor — Agent B → L1)
from l1_compute.analysis.mtf_iv_engine import MTFIVEngine
from l1_compute.analysis.volume_imbalance_engine import VolumeImbalanceEngine
from l1_compute.analysis.jump_detector import JumpDetector
from l1_compute.trackers.iv_velocity_tracker import IVVelocityTracker
from l1_compute.trackers.mtf_iv_persistence import MTFIVWindowPersistence
from l1_compute.trackers.vanna_flow_analyzer import VannaFlowAnalyzer
from l1_compute.trackers.wall_migration_tracker import WallMigrationTracker

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
        mtf_window_persistence: Optional MTFIVWindowPersistence (injected for testing).
    """

    def __init__(
        self,
        r: float = 0.05,
        q: float = 0.0,
        sabr_enabled: bool = True,
        iv_ws_ttl: float = 7200.0,
        mtf_window_persistence: MTFIVWindowPersistence | None = None,
    ) -> None:
        self._r = r
        self._q = q

        # Core L1 pipeline components
        self._router      = ComputeRouter()
        self._aggregator  = StreamingAggregator()
        self._iv_resolver = IVResolver(ws_ttl=iv_ws_ttl)
        self._sabr        = SABRCalibrator() if sabr_enabled else None
        self._inst        = L1Instrumentation()
        self._last_sabr_at: float = 0.0

        # Microstructure (per-symbol, lazily created)
        self._vpin_map: dict[str, VPINv2] = {}
        self._bbo       = BBOv2()
        self._vol_accel = VolAccelV2()

        # Trackers (Phase 1 Refactor)
        self._iv_tracker      = IVVelocityTracker()
        self._wall_tracker    = WallMigrationTracker()
        self._vanna_analyzer  = VannaFlowAnalyzer()
        self._mtf_iv_engine   = MTFIVEngine()
        self._vib_engine      = VolumeImbalanceEngine()
        self._jump_detector   = JumpDetector()

        # MTF buffers (per-timeframe geometric frames)
        self._MTF_INTERVALS: dict[str, float] = {"1m": 60.0, "5m": 300.0, "15m": 900.0}
        self._mtf_buf:       dict[str, list[tuple[float, float]]] = {
            "1m": [], "5m": [], "15m": []
        }
        self._mtf_last_push: dict[str, float] = {"1m": 0.0, "5m": 0.0, "15m": 0.0}

        if mtf_window_persistence is not None:
            self._mtf_persistence = mtf_window_persistence
        else:
            try:
                self._mtf_persistence = MTFIVWindowPersistence()
            except Exception as exc:
                logger.error("[L1ComputeReactor] MTF persistence init failed: %s", exc)
                self._mtf_persistence = None

        # Microstructure signal builder (DI — receives tracker references)
        self._micro_builder = MicroSignalBuilder(
            vpin_map=self._vpin_map,
            bbo=self._bbo,
            vol_accel=self._vol_accel,
            iv_tracker=self._iv_tracker,
            wall_tracker=self._wall_tracker,
            vanna_analyzer=self._vanna_analyzer,
            mtf_iv_engine=self._mtf_iv_engine,
            vib_engine=self._vib_engine,
            jump_detector=self._jump_detector,
            mtf_buf=self._mtf_buf,
            mtf_last_push=self._mtf_last_push,
            mtf_intervals=self._MTF_INTERVALS,
            mtf_persistence=self._mtf_persistence,
        )

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
            chain_snapshot: Option entries from L0/ChainStateStore.
            spot:           Current underlying spot price.
            l0_version:     L0 MVCC version for provenance.
            iv_cache:       REST IV baseline {symbol: iv}.
            spot_at_sync:   {symbol: spot_at_last_iv_sync}.
            extra_metadata: Audit / diagnostics pass-through.

        Returns:
            Immutable EnrichedSnapshot ready for L2 Decision Layer.
        """
        if not chain_snapshot or spot <= 0:
            return self._empty_snapshot(l0_version, extra_metadata=extra_metadata or {})

        iv_cache     = iv_cache     or {}
        spot_at_sync = spot_at_sync or {}

        with self._inst.span_compute():
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
        """Update BBO imbalance from a depth push event (call from asyncio loop)."""
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
        extra_metadata: Optional[dict[str, Any]] = None,
    ) -> EnrichedSnapshot:
        """Full pipeline (runs in thread pool via asyncio.to_thread)."""
        extra_metadata = extra_metadata or {}
        t_start = time.monotonic()
        now     = datetime.now(_ET)

        # Normalise to RecordBatch (zero-copy where possible)
        rb = ensure_record_batch(chain_snapshot)
        n  = rb.num_rows
        self._inst.set_chain_size(n)

        if n == 0 or spot <= 0.0:
            logger.debug("[L1ComputeReactor] Skipping: snapshot empty or spot <= 0")
            return self._empty_snapshot(l0_version, extra_metadata=extra_metadata)

        # Step 1 — IV Resolution
        ttm_years = get_trading_ttm_v2_scalar(now)
        with self._inst.span_iv_resolution():
            resolved_ivs = self._iv_resolver.batch_resolve(
                chain_snapshot, spot, iv_cache, spot_at_sync, ttm_years=ttm_years
            )

        # Step 2 — Conditional SABR recalibration
        if (
            self._sabr is not None
            and (time.monotonic() - self._last_sabr_at) >= _SABR_RECALIBRATE_INTERVAL
        ):
            try:
                dicts_for_sabr = (
                    chain_snapshot
                    if isinstance(chain_snapshot, list)
                    else rb.to_pylist()
                )
                self._sabr.calibrate_from_chain(dicts_for_sabr, forward=spot, ttm=ttm_years)
                self._last_sabr_at = time.monotonic()
            except Exception as exc:
                logger.debug("[L1ComputeReactor] SABR calibration skipped: %s", exc)

        # Step 3 — Build arrays for batch compute (zero-copy numpy)
        spots_arr   = np.full(n, spot, dtype=np.float64)
        strikes_arr = rb.column("strike").to_numpy()
        is_call_arr = rb.column("is_call").to_numpy(zero_copy_only=False)
        ois_arr     = rb.column("open_interest").to_numpy()
        mults_arr   = rb.column("contract_multiplier").to_numpy()

        symbols    = rb.column("symbol").to_pylist()
        ivs_arr    = np.zeros(n, dtype=np.float64)
        valid_mask = np.zeros(n, dtype=np.bool_)
        iv_missing = 0

        for i, sym in enumerate(symbols):
            rv = resolved_ivs.get(sym)
            if rv is None or not rv.is_valid:
                iv_missing += 1
            else:
                ivs_arr[i]    = rv.value
                valid_mask[i] = True

        n_valid  = int(np.sum(valid_mask))
        iv_stats = self._iv_resolver.stats

        if n_valid == 0:
            logger.info("[L1ComputeReactor] compute bypassed: n_valid=0 (n=%d)", n)
            return self._empty_snapshot(l0_version, extra_metadata=extra_metadata)

        # Step 4 — Greeks batch compute
        t_greeks = time.monotonic()
        with self._inst.span_greeks_kernel():
            matrix, decision = self._router.compute(
                spots_arr, strikes_arr, ivs_arr, ttm_years, is_call_arr,
                r=self._r, q=self._q, ois=ois_arr, mults=mults_arr,
            )
        compute_audit = extra_metadata.get("compute_audit", {}) if isinstance(extra_metadata, dict) else {}
        if isinstance(compute_audit, dict):
            logger.info(
                "[GPU-AUDIT] l1_dispatch tick_id=%s snapshot_version=%s compute_id=%s "
                "gpu_task_id=%s tier=%s chain_size=%s",
                compute_audit.get("tick_id"),
                compute_audit.get("snapshot_version", l0_version),
                compute_audit.get("compute_id"),
                compute_audit.get("gpu_task_id"),
                decision.tier.value,
                n_valid,
            )
        greeks_ms = (time.monotonic() - t_greeks) * 1000.0
        self._inst.record_greeks_latency(greeks_ms / 1000.0)
        self._inst.record_compute_tier(decision.tier.value)

        # Step 5 — Streaming aggregation
        t_agg = time.monotonic()
        with self._inst.span_aggregation():
            self._aggregator.full_recompute(
                matrix,
                strikes_arr,
                is_call_arr,
                symbols=symbols,
                spot=spot,
                ivs=ivs_arr,
                ois=ois_arr,
                mults=mults_arr,
                t_years=ttm_years,
                r=self._r,
                q=self._q,
            )
            agg = self._aggregator.snapshot()
        agg_ms = (time.monotonic() - t_agg) * 1000.0

        atm_iv = self._extract_atm_iv(strikes_arr[valid_mask], ivs_arr[valid_mask], spot)

        # Arrow output columns
        out_batch = rb.append_column("computed_iv",    pa.array(ivs_arr))
        out_batch = out_batch.append_column("computed_delta", pa.array(matrix.delta))
        out_batch = out_batch.append_column("computed_gamma", pa.array(matrix.gamma))
        out_batch = out_batch.append_column("computed_vanna", pa.array(matrix.vanna))
        out_batch = out_batch.append_column("gex",            pa.array(matrix.gex_per_contract))
        out_batch = out_batch.append_column("call_gex",       pa.array(matrix.call_gex))
        out_batch = out_batch.append_column("put_gex",        pa.array(matrix.put_gex))

        # Step 6 — Microstructure composite (delegated to MicroSignalBuilder)
        with self._inst.span_microstructure():
            micro_sig = self._micro_builder.build(
                chain_snapshot=chain_snapshot,
                spot=spot,
                now=now,
                atm_iv=atm_iv,
                net_gex=agg.net_gex,
                call_wall=agg.call_wall,
                call_wall_gex=agg.call_wall_gex,
                put_wall=agg.put_wall,
                put_wall_gex=agg.put_wall_gex,
            )

        # Step 7 — Quality report
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
            sabr_rmse=(
                self._sabr.params.calibration_error
                if (self._sabr and self._sabr.params) else 0.0
            ),
        )

        out_agg = OutAggregateGreeks(
            net_gex=agg.net_gex,
            net_vanna_raw_sum=agg.net_vanna_raw_sum,
            net_vanna=agg.net_vanna,
            net_charm_raw_sum=agg.net_charm_raw_sum,
            net_charm=agg.net_charm,
            call_wall=agg.call_wall,
            call_wall_gex=agg.call_wall_gex,
            put_wall=agg.put_wall,
            put_wall_gex=agg.put_wall_gex,
            flip_level=agg.flip_level,
            flip_level_cumulative=agg.flip_level_cumulative,
            zero_gamma_level=agg.zero_gamma_level,
            atm_iv=atm_iv,
            total_call_gex=agg.total_call_gex,
            total_put_gex=agg.total_put_gex,
            num_contracts=n_valid,
            per_strike_gex=agg.per_strike_gex,
        )

        ttm_seconds = ttm_years * 252.0 * 6.5 * 3600.0
        total_ms    = (time.monotonic() - t_start) * 1000.0
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

    # ── Static utilities ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_atm_iv(
        strikes: np.ndarray,
        ivs: np.ndarray,
        spot: float,
    ) -> float:
        """IV of the option strike closest to ATM."""
        if len(strikes) == 0:
            return 0.0
        idx = int(np.argmin(np.abs(strikes - spot)))
        return float(ivs[idx]) if ivs[idx] > 0 else 0.0

    def _empty_snapshot(
        self,
        l0_version: int,
        extra_metadata: Optional[dict[str, Any]] = None,
    ) -> EnrichedSnapshot:
        return EnrichedSnapshot(
            spot=0.0,
            chain=None,
            aggregates=OutAggregateGreeks(),
            microstructure=MicroSignals(),
            quality=ComputeQualityReport(),
            ttm_seconds=0.0,
            version=l0_version,
            computed_at=datetime.now(_ET),
            extra_metadata=dict(extra_metadata or {}),
        )

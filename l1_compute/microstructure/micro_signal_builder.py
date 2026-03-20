"""Microstructure signal builder — assembles MicroSignals from all L1 trackers.

Extracted from L1ComputeReactor._build_micro_signals() (lines 424–637).

Responsibilities:
    - VPIN composite + ATM VPIN selection
    - BBO aggregation
    - VolAccel phase classification
    - Tracker coordination: VannaFlowAnalyzer, WallMigrationTracker,
      IVVelocityTracker, MTFIVEngine, VolumeImbalanceEngine, JumpDetector
    - OTM call/put volume segmentation
    - Squeeze alert derivation
    - MicroSignals assembly

Receives all tracker references via constructor DI — no direct import
of reactor internals. Fully decoupled from the reactor orchestration loop.

Layer:  L1
Deps:   l1_compute/trackers/*, l1_compute/microstructure/*, shared/
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Union

import pyarrow as pa

from shared.config import settings
from l1_compute.microstructure.bbo_v2 import BBOv2
from l1_compute.microstructure.vpin_v2 import VPINv2, VPINRegime
from l1_compute.microstructure.vol_accel_v2 import VolAccelV2
from l1_compute.microstructure.wall_context_builder import build_wall_context
from l1_compute.output.enriched_snapshot import MicroSignals
from l1_compute.trackers.iv_velocity_tracker import IVVelocityTracker
from l1_compute.trackers.mtf_iv_persistence import MTFIVWindowPersistence
from l1_compute.trackers.vanna_flow_analyzer import VannaFlowAnalyzer
from l1_compute.trackers.wall_migration_tracker import WallMigrationTracker
from l1_compute.analysis.mtf_iv_engine import MTFIVEngine
from l1_compute.analysis.volume_imbalance_engine import VolumeImbalanceEngine
from l1_compute.analysis.jump_detector import JumpDetector

# Wall strike bandwidth for representative volume aggregation (dollars)
_WALL_VOL_BAND: float = 2.0


class MicroSignalBuilder:
    """Assembles MicroSignals from live tracker state.

    Instantiated once by L1ComputeReactor and called on every tick.
    All tracker dependencies are injected via constructor.

    Args:
        vpin_map:       Per-symbol VPINv2 tracker map (shared ref).
        bbo:            BBOv2 instance.
        vol_accel:      VolAccelV2 instance.
        iv_tracker:     IVVelocityTracker instance.
        wall_tracker:   WallMigrationTracker instance.
        vanna_analyzer: VannaFlowAnalyzer instance.
        mtf_iv_engine:  MTFIVEngine instance.
        vib_engine:     VolumeImbalanceEngine instance.
        jump_detector:  JumpDetector instance.
        mtf_buf:        MTF buffer dict (shared ref).
        mtf_last_push:  MTF last-push timestamps (shared ref).
        mtf_intervals:  MTF interval seconds dict.
        mtf_persistence: Optional MTFIVWindowPersistence.
    """

    def __init__(
        self,
        vpin_map: dict[str, VPINv2],
        bbo: BBOv2,
        vol_accel: VolAccelV2,
        iv_tracker: IVVelocityTracker,
        wall_tracker: WallMigrationTracker,
        vanna_analyzer: VannaFlowAnalyzer,
        mtf_iv_engine: MTFIVEngine,
        vib_engine: VolumeImbalanceEngine,
        jump_detector: JumpDetector,
        mtf_buf: dict[str, list[tuple[float, float]]],
        mtf_last_push: dict[str, float],
        mtf_intervals: dict[str, float],
        mtf_persistence: MTFIVWindowPersistence | None,
    ) -> None:
        self._vpin_map        = vpin_map
        self._bbo             = bbo
        self._vol_accel       = vol_accel
        self._iv_tracker      = iv_tracker
        self._wall_tracker    = wall_tracker
        self._vanna_analyzer  = vanna_analyzer
        self._mtf_iv_engine   = mtf_iv_engine
        self._vib_engine      = vib_engine
        self._jump_detector   = jump_detector
        self._mtf_buf         = mtf_buf
        self._mtf_last_push   = mtf_last_push
        self._mtf_intervals   = mtf_intervals
        self._mtf_persistence = mtf_persistence

    # ── Primary entry point ───────────────────────────────────────────────────

    def build(
        self,
        chain_snapshot: Union[list[dict], pa.RecordBatch],
        spot: float,
        now: datetime,
        atm_iv: float,
        net_gex: float,
        call_wall: float,
        call_wall_gex: float,
        put_wall: float,
        put_wall_gex: float,
    ) -> MicroSignals:
        """Compute and return MicroSignals for the current tick."""
        sim_clock_mono = time.monotonic()

        # MTF persistence bootstrap
        mtf_date: str | None = None
        if self._mtf_persistence is not None:
            mtf_date = self._mtf_persistence.bootstrap_day(
                now_et=now, engine=self._mtf_iv_engine
            )

        # Normalise chain to list for iteration
        if isinstance(chain_snapshot, pa.RecordBatch):
            entries     = chain_snapshot.to_pylist()
            total_vol   = float(sum(e.get("volume", 0) for e in entries))
        else:
            entries   = chain_snapshot
            total_vol = sum(float(e.get("volume", 0)) for e in entries)

        # ── 1. Base signals ───────────────────────────────────────────────────
        composite_vpin, first_vpin = self._aggregate_vpin(chain_snapshot, spot)
        bbo_imbalance, bbo_ewma_fast, bbo_ewma_slow, bbo_persist = self._aggregate_bbo()
        phase  = self._vol_accel.classify_phase(now.hour, now.minute)
        va_sig = self._vol_accel.update_from_cumulative(total_vol, phase)
        regime = (first_vpin.tf_1m.regime if first_vpin else VPINRegime.NORMAL)

        # ── 2. Vanna Flow ─────────────────────────────────────────────────────
        vanna_result = self._vanna_analyzer.update(
            spot=spot,
            atm_iv=atm_iv,
            net_gex=net_gex,
            spy_atm_iv=atm_iv,
            sim_clock_mono=sim_clock_mono,
        )
        wall_mult = vanna_result.wall_displacement_multiplier if vanna_result else 1.0

        # ── 3. Wall Migration ────────────────────────────────────────────────
        call_wall_volume, put_wall_volume = self._compute_wall_volumes(
            entries, call_wall, put_wall
        )
        wall_result = self._wall_tracker.update(
            call_wall=call_wall,
            put_wall=put_wall,
            spot=spot,
            call_wall_volume=call_wall_volume,
            put_wall_volume=put_wall_volume,
            sim_clock_mono=sim_clock_mono,
            displacement_multiplier=wall_mult,
        )
        wall_context = build_wall_context(
            chain_snapshot,
            net_gex=net_gex,
            call_wall=call_wall,
            put_wall=put_wall,
            call_wall_gex=call_wall_gex,
            put_wall_gex=put_wall_gex,
        )
        wall_payload = wall_result.model_dump() if wall_result else None
        if isinstance(wall_payload, dict):
            wall_payload["wall_context"] = wall_context

        # ── 4. IV Velocity + MTF Engine ──────────────────────────────────────
        iv_result = self._iv_tracker.update(
            spot=spot, atm_iv=atm_iv, sim_clock_mono=sim_clock_mono
        )
        has_mtf_update = self._update_mtf_buffers(atm_iv, sim_clock_mono)
        if has_mtf_update and self._mtf_persistence is not None and mtf_date is not None:
            self._mtf_persistence.persist_snapshot(
                date_str=mtf_date,
                now_et=now,
                engine=self._mtf_iv_engine,
            )
        mtf_consensus = self._mtf_iv_engine.compute()

        # ── 5. Volume Imbalance + Jump Detection ─────────────────────────────
        otm_call_vol, otm_put_vol = self._split_otm_volumes(entries, spot)
        vib_result  = self._vib_engine.update(
            entries,
            spot,
            otm_call_vol=otm_call_vol,
            otm_put_vol=otm_put_vol,
            current_cumulative_total_chain_vol=int(total_vol),
        )
        jump_result = self._jump_detector.update(spot)

        # ── 6. Squeeze alert ─────────────────────────────────────────────────
        vol_accel_val        = vib_result.vol_accel_ratio if vib_result else 1.0
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
            bbo_imbalance_raw=bbo_imbalance,
            bbo_ewma_fast=bbo_ewma_fast,
            bbo_ewma_slow=bbo_ewma_slow,
            bbo_persistence=bbo_persist,
            vol_accel_ratio=va_sig.ratio,
            vol_accel_threshold=va_sig.threshold,
            vol_accel_elevated=va_sig.is_elevated,
            vol_entropy=va_sig.entropy,
            session_phase=phase.value,
            iv_velocity=iv_result.model_dump() if iv_result else None,
            mtf_consensus=mtf_consensus,
            iv_confidence=self._iv_tracker.get_confidence(),
            wall_migration=wall_payload,
            wall_context=wall_context,
            wall_confidence=self._wall_tracker.get_confidence(),
            vanna_flow_result=vanna_result.model_dump() if vanna_result else None,
            vanna_confidence=self._vanna_analyzer.get_confidence(),
            volume_imbalance=vib_result.model_dump() if vib_result else None,
            jump_detection=jump_result.model_dump() if jump_result else None,
            dealer_squeeze_alert=dealer_squeeze_alert,
            avg_atm_vpin_score=0.0,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _aggregate_vpin(
        self,
        chain_snapshot: Union[list[dict], pa.RecordBatch],
        spot: float,
    ) -> tuple[float, Any]:
        """Return (composite_vpin_score, atm_vpin_signal)."""
        if not self._vpin_map:
            return 0.0, None

        all_scores = [v.get_signal().composite_score for v in self._vpin_map.values()]
        composite  = sum(all_scores) / len(all_scores)

        # ATM VPIN: symbol closest to spot (by strike distance)
        atm_signal = None
        best_dist  = float("inf")

        snap_list = (
            chain_snapshot.to_pylist()
            if isinstance(chain_snapshot, pa.RecordBatch)
            else chain_snapshot
        )
        for sym, vpin in self._vpin_map.items():
            strike_val: float | None = None
            for entry in snap_list:
                if entry.get("symbol") == sym:
                    strike_val = float(entry.get("strike") or 0.0)
                    break
            if strike_val and strike_val > 0:
                dist = abs(strike_val - spot)
                if dist < best_dist:
                    best_dist  = dist
                    atm_signal = vpin.get_signal()

        if atm_signal is None:
            atm_signal = list(self._vpin_map.values())[0].get_signal()

        return composite, atm_signal

    def _aggregate_bbo(self) -> tuple[float, float, float, float]:
        """Return (avg_imbalance, avg_ewma_fast, avg_ewma_slow, avg_persist)."""
        bbo_snap = self._bbo.get_all_snapshot()
        if not bbo_snap:
            return 0.0, 0.0, 0.0, 0.0
        n = len(bbo_snap)
        return (
            sum(s.raw_imbalance for s in bbo_snap.values()) / n,
            sum(s.ewma_fast     for s in bbo_snap.values()) / n,
            sum(s.ewma_slow     for s in bbo_snap.values()) / n,
            sum(s.persistence   for s in bbo_snap.values()) / n,
        )

    @staticmethod
    def _compute_wall_volumes(
        entries: list[dict],
        call_wall: float,
        put_wall: float,
    ) -> tuple[float, float]:
        """Return (call_wall_volume, put_wall_volume) within ±_WALL_VOL_BAND."""
        call_vol = 0.0
        put_vol  = 0.0
        if not (call_wall > 0 or put_wall > 0):
            return call_vol, put_vol
        for e in entries:
            strike = float(e.get("strike") or 0.0)
            vol    = float(e.get("volume") or 0.0)
            if call_wall > 0 and abs(strike - call_wall) <= _WALL_VOL_BAND:
                call_vol += vol
            if put_wall > 0 and abs(strike - put_wall) <= _WALL_VOL_BAND:
                put_vol += vol
        return call_vol, put_vol

    @staticmethod
    def _split_otm_volumes(entries: list[dict], spot: float) -> tuple[float, float]:
        """Return (otm_call_volume, otm_put_volume)."""
        otm_call = 0.0
        otm_put  = 0.0
        for e in entries:
            strike   = float(e.get("strike") or 0.0)
            vol      = float(e.get("volume") or 0.0)
            opt_type = str(e.get("type") or e.get("opt_type") or "").upper()
            if opt_type == "CALL" and strike > spot:
                otm_call += vol
            elif opt_type == "PUT" and strike < spot:
                otm_put += vol
        return otm_call, otm_put

    def _update_mtf_buffers(self, atm_iv: float, sim_clock_mono: float) -> bool:
        """Push IV into MTF buffers and trigger frame updates. Returns True if any frame updated."""
        if atm_iv <= 0:
            return False
        did_any = False
        for tf, interval in self._mtf_intervals.items():
            self._mtf_buf[tf].append((sim_clock_mono, atm_iv))
            if (sim_clock_mono - self._mtf_last_push[tf]) >= interval:
                buf = self._mtf_buf[tf]
                if len(buf) >= 2:
                    start_ts, start_iv = buf[0]
                    end_ts,   end_iv   = buf[-1]
                    dt = max(end_ts - start_ts, 1e-6)
                    self._mtf_iv_engine.update_frame(
                        tf,
                        start_iv=float(start_iv),
                        end_iv=float(end_iv),
                        dt_seconds=float(dt),
                    )
                    did_any = True
                self._mtf_buf[tf].clear()
                self._mtf_last_push[tf] = sim_clock_mono
        return did_any

"""l3_assembly.assembly.ui_state_tracker — Stateful tracking for UI presenters.

Maintains historical state (e.g. wall migration history) needed by the frontend
but omitted from the stateless L1/L2 numerical pipeline.
"""

from __future__ import annotations

import time
from typing import Any

from shared.config import settings
from shared.system.tactical_triad_logic import (
    classify_vrp_state,
    compute_vrp,
    normalize_svol_state,
    resolve_svol_fields,
)
from l1_compute.trackers.vanna_flow_analyzer import VannaFlowAnalyzer
from l1_compute.trackers.wall_migration_tracker import WallMigrationTracker
from l1_compute.analysis.mtf_iv_engine import MTFIVEngine


class UIStateTracker:
    """Maintains stateful UI metrics (Wall Migration, Vanna Flow, MTF IV).
    
    Used by L3AssemblyReactor to enrich the stateless L1/L2 snapshots.
    """

    def __init__(self) -> None:
        self._vanna_analyzer = VannaFlowAnalyzer()
        self._wall_tracker = WallMigrationTracker()
        self._mtf_iv_engine = MTFIVEngine()

        # MTF intervals and buffers
        self._MTF_INTERVALS: dict[str, float] = {"1m": 60.0, "5m": 300.0, "15m": 900.0}
        self._mtf_buf: dict[str, list[float]] = {"1m": [], "5m": [], "15m": []}
        self._mtf_last_push: dict[str, float] = {"1m": 0.0, "5m": 0.0, "15m": 0.0}

    async def set_redis_client(self, client: Any) -> None:
        """Inject shared Redis client."""
        await self._vanna_analyzer.set_redis_client(client)
        self._wall_tracker.set_redis_client(client)

    def tick(self, snapshot: Any, decision: Any) -> dict[str, Any]:
        """Update trackers and return UI-formatted dictionary."""
        now_mono = time.monotonic()
        
        def _get(obj, attr, default=0.0):
            if hasattr(obj, attr):
                return getattr(obj, attr)
            if isinstance(obj, dict):
                return obj.get(attr, default)
            return default

        try:
            spot = float(_get(snapshot, "spot"))
            
            # Extract aggregates
            if hasattr(snapshot, "aggregates"):
                agg = snapshot.aggregates
            elif isinstance(snapshot, dict):
                agg = snapshot.get("aggregates", snapshot) # fallback to self if flat
            else:
                import logging
                logging.getLogger(__name__).error(f"[UIStateTracker] Unsupported snapshot type: {type(snapshot)}")
                return {}

            atm_iv = float(_get(agg, "atm_iv"))
            net_gex = float(_get(agg, "net_gex"))
            call_wall = float(_get(agg, "call_wall"))
            put_wall = float(_get(agg, "put_wall"))
            net_charm = float(_get(agg, "net_charm"))
            
            # Using 0 for volumes as they are only used for some advanced micro features that we can bypass here
            call_wall_vol = 0 
            put_wall_vol = 0
            
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            import logging
            logging.getLogger(__name__).error(f"[UIStateTracker] Extraction failed: {e}")
            return {}

        # 1. Vanna Flow
        vanna_result = self._vanna_analyzer.update(
            spot=spot,
            atm_iv=atm_iv,
            net_gex=net_gex,
            spy_atm_iv=atm_iv,
            sim_clock_mono=now_mono,
        )
        wall_mult = vanna_result.wall_displacement_multiplier if vanna_result else 1.0

        # 2. Wall Migration
        wall_result = self._wall_tracker.update(
            call_wall=call_wall,
            put_wall=put_wall,
            spot=spot,
            call_wall_volume=call_wall_vol,
            put_wall_volume=put_wall_vol,
            sim_clock_mono=now_mono,
            displacement_multiplier=wall_mult,
        )

        # 3. MTF Consensus
        if atm_iv > 0:
            for tf, interval in self._MTF_INTERVALS.items():
                self._mtf_buf[tf].append(atm_iv)
                if (now_mono - self._mtf_last_push[tf]) >= interval:
                    bar_mean = sum(self._mtf_buf[tf]) / len(self._mtf_buf[tf])
                    self._mtf_iv_engine.update(tf, bar_mean)
                    self._mtf_buf[tf].clear()
                    self._mtf_last_push[tf] = now_mono

        mtf_consensus = self._mtf_iv_engine.compute({
            "1m": atm_iv,
            "5m": atm_iv,
            "15m": atm_iv,
        })
        
        # 4. Tactical Triad (VRP)
        vrp = compute_vrp(atm_iv, getattr(settings, "vrp_baseline_hv", 13.5))
        vrp_state = classify_vrp_state(
            vrp,
            getattr(settings, "vrp_cheap_threshold", -2.0),
            getattr(settings, "vrp_expensive_threshold", 2.0),
            getattr(settings, "vrp_trap_threshold", 5.0),
        )

        # Extract regime from vanna
        vanna_state_raw = vanna_result.state.value if vanna_result and hasattr(vanna_result.state, "value") else "UNAVAILABLE"
        vanna_state_str = normalize_svol_state(vanna_state_raw)
        gex_regime_str = vanna_result.gex_regime.value if vanna_result and hasattr(vanna_result.gex_regime, "value") else "NEUTRAL"
        svol_corr, svol_state = resolve_svol_fields(vanna_result)
        
        # Skew Dynamics (approx 25d skew)
        skew_dynamics = {}
        features = getattr(decision, "feature_vector", {}) if decision else {}
        skew_val = features.get("skew_25d_normalized", 0.0)
        
        skew_state = "NEUTRAL"
        if skew_val < getattr(settings, 'skew_speculative_max', -0.15):
            skew_state = "SPECULATIVE"
        elif skew_val > getattr(settings, 'skew_defensive_min', 0.15):
            skew_state = "DEFENSIVE"
            
        skew_dynamics = {
            "skew_value": skew_val,
            "skew_state": skew_state,
        }
        
        momentum_direction = "NEUTRAL"
        try:
            if decision and hasattr(decision, "signal_summary"):
                mom_sig = decision.signal_summary.get("momentum_signal", "NEUTRAL")
                if isinstance(mom_sig, dict):
                    momentum_direction = mom_sig.get("direction", "NEUTRAL")
                else:
                    momentum_direction = str(mom_sig)
        except AttributeError:
            pass

        # 5. Consolidated Microstructure (For L3 Payload)
        # Pull from EnrichedSnapshot.microstructure if available, 
        # otherwise fallback to decision data or empty.
        ms_out = {}
        if hasattr(snapshot, "microstructure") and snapshot.microstructure:
            ms = snapshot.microstructure
            ms_out = {
                "iv_velocity": getattr(ms, "iv_velocity", None),
                "wall_migration": getattr(ms, "wall_migration", None),
                "vanna_flow_result": getattr(ms, "vanna_flow_result", None),
                "mtf_consensus": getattr(ms, "mtf_consensus", None),
                "volume_imbalance": getattr(ms, "volume_imbalance", None),
                "jump_detection": getattr(ms, "jump_detection", None),
                "dealer_squeeze_alert": getattr(ms, "dealer_squeeze_alert", False),
                "iv_confidence": getattr(ms, "iv_confidence", 0.0),
                "wall_confidence": getattr(ms, "wall_confidence", 0.0),
                "vanna_confidence": getattr(ms, "vanna_confidence", 0.0),
            }
        else:
            # Fallback for legacy dict snapshots
            if isinstance(snapshot, dict):
                ms_raw = snapshot.get("micro_structure", {}).get("micro_structure_state") or \
                         snapshot.get("microstructure", {})
            else:
                ms_raw = {}
            if isinstance(ms_raw, dict):
                ms_out = ms_raw

        return {
            "wall_migration_data": wall_result.model_dump() if wall_result else {},
            "mtf_consensus": mtf_consensus,
            "vanna_state": vanna_state_str,
            "gex_regime": gex_regime_str,
            "vrp": vrp,
            "vrp_state": vrp_state,
            "net_charm": net_charm,
            "skew_dynamics": skew_dynamics,
            "momentum": momentum_direction,
            "svol_corr": svol_corr,
            "svol_state": svol_state,
            "micro_structure": {"micro_structure_state": ms_out}
        }

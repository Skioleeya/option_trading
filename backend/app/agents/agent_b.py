"""Agent B — Options Structure / Trap Detection.

Detects divergence between spot price movement and option price action
to identify bull traps and bear traps.

Also orchestrates microstructure analysis (IV velocity, wall migration, vanna flow).
"""

from __future__ import annotations

import enum
import logging
import time
from collections import deque
from datetime import datetime
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from app.agents.base import AgentResult
from app.agents.services.greeks_extractor import GreeksExtractor
from app.config import settings
from app.services.analysis.mtf_iv_engine import MTFIVEngine
from app.services.analysis.volume_imbalance_engine import VolumeImbalanceEngine
from app.services.analysis.jump_detector import JumpDetector
from app.services.trackers.iv_velocity_tracker import IVVelocityTracker
from app.services.trackers.vanna_flow_analyzer import VannaFlowAnalyzer
from app.services.trackers.wall_migration_tracker import WallMigrationTracker


logger = logging.getLogger(__name__)


class DivergenceState(str, enum.Enum):
    """Divergence state between spot and options."""
    IDLE = "IDLE"
    ACTIVE_BULL_TRAP = "ACTIVE_BULL_TRAP"
    ACTIVE_BEAR_TRAP = "ACTIVE_BEAR_TRAP"


class _RocPoint(NamedTuple):
    timestamp_mono: float
    spot: float
    call_mark: float
    put_mark: float


class AgentB1:
    """Options structure divergence detector (Trap Machine).

    Logic:
    - BULL TRAP: Price rising + Call option value dying = fake rally
    - BEAR TRAP: Price dropping + Put option value dying = fake selloff

    Also runs microstructure analysis:
    - IV Velocity tracking
    - Wall Migration tracking
    - Vanna Flow analysis
    """

    AGENT_ID = "agent_b1"

    def __init__(self) -> None:
        self._history: deque[_RocPoint] = deque(maxlen=300)
        self._state = DivergenceState.IDLE
        self._entry_count = 0
        self._exit_count = 0
        self._last_run_time: float = 0.0
        self._gamma_flip_cooldown: int = 0

        # PP-5 FIX: Track when trap machine vs micro last ran independently.
        # This exposes the dual-rate staleness gap to AgentG for diagnostics.
        self._trap_updated_at: float = 0.0   # monotonic time of last full trap recompute
        self._micro_updated_at: float = 0.0  # monotonic time of last micro update

        # Greeks extractor
        self._greeks_extractor = GreeksExtractor()

        # Microstructure trackers (v2.0)
        self._iv_tracker = IVVelocityTracker()
        self._wall_tracker = WallMigrationTracker()
        self._vanna_analyzer = VannaFlowAnalyzer()

        # MTF trackers (Multi-Timeframe) — legacy IVVelocity (kept for backward compat)
        self._iv_tracker_1m = IVVelocityTracker(window_seconds=settings.mtf_window_seconds_1min)
        self._iv_tracker_5m = IVVelocityTracker(window_seconds=settings.mtf_window_seconds_5min)
        self._iv_tracker_15m = IVVelocityTracker(window_seconds=settings.mtf_window_seconds_15min)

        # MTF IV Z-Score Engine (Phase 23 — VSRSD Method C)
        self._mtf_iv_engine = MTFIVEngine()

        # FIX E: Per-timeframe sampling buffers so each TF accumulates its own
        # mean-bar before pushing to MTFIVEngine (prevents all-three-identical input).
        # Keys match MTFIVEngine timeframe names exactly.
        self._MTF_INTERVALS: dict[str, float] = {"1m": 60.0, "5m": 300.0, "15m": 900.0}
        self._mtf_buf: dict[str, list[float]] = {"1m": [], "5m": [], "15m": []}
        self._mtf_last_push: dict[str, float] = {"1m": 0.0, "5m": 0.0, "15m": 0.0}

        # Volume Imbalance Engine (Phase 24 — C/P Volume Imbalance)
        self._vib_engine = VolumeImbalanceEngine()

        # Jump Detector (Phase 27 — Paper 5 Safety Valve)
        self._jump_detector = JumpDetector()

    async def set_redis_client(self, client: Any) -> None:
        """Inject shared Redis client into sub-trackers."""
        await self._vanna_analyzer.set_redis_client(client)
        self._wall_tracker.set_redis_client(client)

    def run(self, snapshot: dict[str, Any]) -> AgentResult:
        """Process market snapshot and detect traps.

        Args:
            snapshot: Market data dict with keys:
                spot, call_mark, put_mark, chain, volume, etc.
        """
        now = datetime.now(ZoneInfo("US/Eastern"))
        now_mono = time.monotonic()
        
        spot = snapshot.get("spot")
        call_mark = snapshot.get("call_mark", 0) or 0
        put_mark = snapshot.get("put_mark", 0) or 0
        chain = snapshot.get("chain", [])

        if not spot or spot <= 0:
            return self._idle_result(now, snapshot)

        # 1. Greeks computation (Always run - lightweight with aggregate_greeks)
        greeks = self._greeks_extractor.compute(
            chain, 
            spot, 
            as_of=now,
            aggregate_greeks=snapshot.get("aggregate_greeks")
        )

        # 2. Microstructure analysis (FIX D: ALWAYS run to prevent blind zones)
        micro = self._run_microstructure(
            chain=chain,
            spot=spot,
            atm_iv=greeks.get("atm_iv"),
            net_gex=greeks.get("net_gex"),
            call_wall=greeks.get("gamma_walls", {}).get("call_wall"),
            put_wall=greeks.get("gamma_walls", {}).get("put_wall"),
            call_wall_volume=0,
            put_wall_volume=0,
            otm_call_vol=greeks.get("otm_call_vol", 0),
            otm_put_vol=greeks.get("otm_put_vol", 0),
            total_chain_vol=greeks.get("total_chain_vol", 0),
            sim_clock_mono=now_mono,
        )

        # Throttle Logic (Only for heavy Trap Detection & Z-Score history)
        elapsed = now_mono - self._last_run_time
        if elapsed < settings.agent_b_gamma_tick_interval and self._last_result:
            # FIX D: Update cached result with FRESH microstructure data.
            # This ensures Agent G always sees the latest Vanna multiplier/Jump status.
            # PP-5 FIX: Also inject dual-rate sync timestamps so AgentG can observe
            # the gap between stale trap state and fresh micro state.
            self._micro_updated_at = now_mono
            sync_gap = now_mono - self._trap_updated_at  # seconds trap is behind micro
            updated_data = dict(self._last_result.data)
            updated_data.update({
                "micro_structure": {"micro_structure_state": micro},
                "iv_confidence": micro.get("iv_confidence", 0),
                "wall_confidence": micro.get("wall_confidence", 0),
                "vanna_confidence": micro.get("vanna_confidence", 0),
                "mtf_consensus": micro.get("mtf_consensus", {}),
                # PP-5 FIX: Dual-rate sync diagnostics
                "trap_computed_at": self._trap_updated_at,
                "micro_computed_at": self._micro_updated_at,
                "trap_micro_sync_gap": round(sync_gap, 3),
            })
            return self._last_result.model_copy(update={"as_of": now, "data": updated_data})

        self._last_run_time = now_mono

        # 3. RoC (Rate of Change) calculation
        self._history.append(_RocPoint(now_mono, spot, call_mark, put_mark))

        # Find T-2 point (within window)
        t2_point = self._find_t2_point(now_mono)

        signal = self._state
        summary_parts = []

        if t2_point is not None:
            # Spot RoC
            spot_roc = ((spot - t2_point.spot) / t2_point.spot) * 100.0 if t2_point.spot > 0 else 0

            # Option RoC
            call_roc = ((call_mark - t2_point.call_mark) / t2_point.call_mark) * 100.0 if t2_point.call_mark > 0 else 0
            put_roc = ((put_mark - t2_point.put_mark) / t2_point.put_mark) * 100.0 if t2_point.put_mark > 0 else 0

            # Trap detection state machine
            signal = self._update_state(spot_roc, call_roc, put_roc)

            if signal == DivergenceState.ACTIVE_BULL_TRAP:
                summary_parts.append(f"Bull Trap: Spot+{spot_roc:.2f}% but Call{call_roc:+.1f}%")
            elif signal == DivergenceState.ACTIVE_BEAR_TRAP:
                summary_parts.append(f"Bear Trap: Spot{spot_roc:+.2f}% but Put{put_roc:+.1f}%")

        # Tactical Triad Metrics Computation
        atm_iv = greeks.get("atm_iv", 0) or 0.0
        # PP-1 FIX: Use configurable baseline HV (was hardcoded 13.5).
        # Override via VRP_BASELINE_HV env var or .env file.
        baseline_hv = settings.vrp_baseline_hv
        vrp = atm_iv - baseline_hv
        
        premium_state = "FAIR"
        if vrp > settings.vrp_trap_threshold:
            premium_state = "TRAP"
        elif vrp > settings.vrp_expensive_threshold:
            premium_state = "EXPENSIVE"
        elif vrp < (settings.vrp_cheap_threshold * 3):
            premium_state = "BARGAIN"
        elif vrp < settings.vrp_cheap_threshold:
            premium_state = "CHEAP"

        hv_analysis = {
            "vrp": vrp,
            "premium_state": premium_state,
        }

        charm_analysis = {
            "net_charm": greeks.get("charm_exposure", 0.0)
        }

        # Skew Dynamics Computation
        skew_ivs = greeks.get("skew_25d", {})
        put_25d_iv = skew_ivs.get("put_25d_iv")
        call_25d_iv = skew_ivs.get("call_25d_iv")
        
        skew_val = 0.0
        skew_state = "NEUTRAL"
        if put_25d_iv and call_25d_iv and atm_iv > 0:
            skew_val = (put_25d_iv - call_25d_iv) / atm_iv
            if skew_val < settings.skew_speculative_max:
                skew_state = "SPECULATIVE"
            elif skew_val > settings.skew_defensive_min:
                skew_state = "DEFENSIVE"
        
        skew_analysis = {
            "skew_value": skew_val,
            "skew_state": skew_state,
        }

        # PP-5 FIX: Record that a full trap recompute just ran (both rates in sync now).
        self._trap_updated_at = now_mono
        self._micro_updated_at = now_mono

        # Build result
        result = AgentResult(
            agent=self.AGENT_ID,
            signal=signal.value if isinstance(signal, DivergenceState) else str(signal),
            as_of=now,
            data={
                "net_gex": greeks.get("net_gex"),
                "spy_atm_iv": greeks.get("spy_atm_iv"),
                "gamma_walls": greeks.get("gamma_walls", {}),
                "gamma_flip": greeks.get("gamma_flip", False),
                "gamma_flip_level": greeks.get("gamma_flip_level"),
                "micro_structure": {
                    "micro_structure_state": micro,
                },
                "iv_confidence": micro.get("iv_confidence", 0),
                "wall_confidence": micro.get("wall_confidence", 0),
                "vanna_confidence": micro.get("vanna_confidence", 0),
                "mtf_consensus": micro.get("mtf_consensus", {}),
                "gamma_profile": greeks.get("gamma_profile", []),
                "per_strike_gex": greeks.get("per_strike_gex", []),
                "top_active_options": chain, # Pass through for presenter
                "hv_analysis": hv_analysis,
                "charm_analysis": charm_analysis,
                "skew_analysis": skew_analysis,
                # PP-5 FIX: Dual-rate sync diagnostics (gap = 0 on full recompute)
                "trap_computed_at": self._trap_updated_at,
                "micro_computed_at": self._micro_updated_at,
                "trap_micro_sync_gap": 0.0,
            },
            summary="; ".join(summary_parts) if summary_parts else "IDLE",
        )
        
        self._last_result = result
        return result

    def _run_microstructure(
        self,
        *,
        chain: list[dict[str, Any]],
        spot: float,
        atm_iv: float | None,
        net_gex: float | None,
        call_wall: float | None,
        put_wall: float | None,
        call_wall_volume: int,
        put_wall_volume: int,
        otm_call_vol: int = 0,
        otm_put_vol: int = 0,
        total_chain_vol: int = 0,
        sim_clock_mono: float | None = None,
    ) -> dict[str, Any]:
        """Run all microstructure trackers."""
        if not settings.agent_b1_v2_enabled:
            return {}

        # 1. Vanna Flow (Dynamic Engine)
        vanna_result = self._vanna_analyzer.update(
            spot=spot,
            atm_iv=atm_iv,
            net_gex=net_gex,
            spy_atm_iv=atm_iv,
            sim_clock_mono=sim_clock_mono,
        )
        
        # Extract dynamic multipliers
        wall_mult = vanna_result.wall_displacement_multiplier if vanna_result else 1.0

        # 2. Wall Migration (Adaptive Sensitivity)
        wall_result = self._wall_tracker.update(
            call_wall=call_wall,
            put_wall=put_wall,
            spot=spot,
            call_wall_volume=call_wall_volume,
            put_wall_volume=put_wall_volume,
            sim_clock_mono=sim_clock_mono,
            displacement_multiplier=wall_mult,
        )

        # 3. IV Velocity
        iv_result = self._iv_tracker.update(
            spot=spot, atm_iv=atm_iv, sim_clock_mono=sim_clock_mono
        )

        # MTF VSRSD: accumulate into per-TF buffers; push bar-mean at each interval
        if atm_iv and atm_iv > 0:
            for tf, interval in self._MTF_INTERVALS.items():
                self._mtf_buf[tf].append(atm_iv)
                if (sim_clock_mono - self._mtf_last_push[tf]) >= interval:
                    bar_mean = sum(self._mtf_buf[tf]) / len(self._mtf_buf[tf])
                    self._mtf_iv_engine.update(tf, bar_mean)
                    self._mtf_buf[tf].clear()
                    self._mtf_last_push[tf] = sim_clock_mono

        # Also run legacy IVVelocityTrackers for backward compat (MTF UI fallback)
        iv_1m  = self._iv_tracker_1m.update(spot=spot,  atm_iv=atm_iv, sim_clock_mono=sim_clock_mono)
        iv_5m  = self._iv_tracker_5m.update(spot=spot,  atm_iv=atm_iv, sim_clock_mono=sim_clock_mono)
        iv_15m = self._iv_tracker_15m.update(spot=spot, atm_iv=atm_iv, sim_clock_mono=sim_clock_mono)

        # Compute VSRSD consensus (new primary path)
        mtf_vsrsd = self._mtf_iv_engine.compute({
            "1m":  atm_iv or 0.0,
            "5m":  atm_iv or 0.0,
            "15m": atm_iv or 0.0,
        })
        mtf_consensus = mtf_vsrsd   # Replaces legacy _compute_mtf_consensus

        # 6. Volume Imbalance (Phase 24)
        vib_result = self._vib_engine.update(
            chain, 
            spot,
            otm_call_vol=otm_call_vol,
            otm_put_vol=otm_put_vol,
            current_cumulative_total_chain_vol=total_chain_vol,
        )

        # 7. Jump Detection (Phase 27)
        jump_result = self._jump_detector.update(spot)

        # 8. Practice 3: Dealer Squeeze Alert
        # Triggered when 1s volume burst is ≥ vol_accel_squeeze_threshold × 60s average
        # AND the GEX regime is negative (dealer delta-hedge exhaustion risk).
        vol_accel = vib_result.vol_accel_ratio if vib_result else 1.0
        dealer_squeeze_alert = (
            vol_accel >= settings.vol_accel_squeeze_threshold
            and net_gex is not None
            and net_gex < 0
        )

        # 9. Practice 2: Propagate average ATM VPIN score
        # The per-strike flow snapshot is not available here (it's held by OptionChainBuilder).
        # We pass a placeholder 0.0; the actual propagation happens in agent_g.py
        # which has access to per_strike_gex with vpin_score fields.
        avg_atm_vpin_score = 0.0

        return {
            "iv_velocity": iv_result.model_dump() if iv_result else None,
            "wall_migration": wall_result.model_dump() if wall_result else None,
            "vanna_flow_result": vanna_result.model_dump() if vanna_result else None,
            "mtf_consensus": mtf_consensus,
            "volume_imbalance": vib_result.model_dump() if vib_result else None,
            "jump_detection": jump_result.model_dump() if jump_result else None,
            "dealer_squeeze_alert": dealer_squeeze_alert,
            "avg_atm_vpin_score": avg_atm_vpin_score,
            "iv_confidence": self._iv_tracker.get_confidence(),
            "wall_confidence": self._wall_tracker.get_confidence(),
            "vanna_confidence": self._vanna_analyzer.get_confidence(),
        }

    def _compute_mtf_consensus(self, iv_1m, iv_5m, iv_15m) -> dict[str, Any]:
        """Compute multi-timeframe consensus from IV velocity across timeframes."""
        directions = {
            "1m": iv_1m.state.value if iv_1m else "UNAVAILABLE",
            "5m": iv_5m.state.value if iv_5m else "UNAVAILABLE",
            "15m": iv_15m.state.value if iv_15m else "UNAVAILABLE",
        }

        # Simple weighted consensus
        bullish_states = {"PAID_MOVE", "ORGANIC_GRIND", "HOLLOW_RISE", "HOLLOW_DROP", "VOL_EXPANSION"}
        bearish_states = {"PAID_DROP"}

        score = 0.0
        w1 = settings.mtf_weight_1min
        w5 = settings.mtf_weight_5min
        w15 = settings.mtf_weight_15min

        for tf, weight in [("1m", w1), ("5m", w5), ("15m", w15)]:
            state = directions[tf]
            if state in bullish_states:
                score += weight
            elif state in bearish_states:
                score -= weight

        if score > 0.3:
            consensus = "BULLISH"
        elif score < -0.3:
            consensus = "BEARISH"
        else:
            consensus = "NEUTRAL"

        return {
            "consensus": consensus,
            "strength": abs(score),
            "timeframes": directions,
        }

    def _find_t2_point(self, now_mono: float) -> _RocPoint | None:
        """Find the T-2 reference point within the valid window."""
        min_span = settings.agent_b_min_window_span
        max_span = settings.agent_b_max_window_span

        for point in reversed(self._history):
            age = now_mono - point.timestamp_mono
            if min_span <= age <= max_span:
                return point

        return None

    def _update_state(
        self,
        spot_roc: float,
        call_roc: float,
        put_roc: float,
    ) -> DivergenceState:
        """Update divergence state machine."""
        th_spot_entry = settings.agent_b_th_spot_entry
        th_spot_exit = settings.agent_b_th_spot_exit
        th_opt_fade = settings.agent_b_th_opt_fade
        th_opt_recover = settings.agent_b_th_opt_recover
        k_entry = settings.agent_b_k_entry
        k_exit = settings.agent_b_k_exit

        if self._state == DivergenceState.IDLE:
            # Check for BULL TRAP entry: Spot up + Call dying
            if spot_roc > th_spot_entry and call_roc < th_opt_fade:
                self._entry_count += 1
                if self._entry_count >= k_entry:
                    logger.debug(f"[L2 Trap] IDLE -> ACTIVE_BULL_TRAP (Spot RoC: {spot_roc:.2f}, Call RoC: {call_roc:.2f})")
                    self._state = DivergenceState.ACTIVE_BULL_TRAP
                    self._exit_count = 0
            # Check for BEAR TRAP entry: Spot down + Put dying
            elif spot_roc < -th_spot_entry and put_roc < th_opt_fade:
                self._entry_count += 1
                if self._entry_count >= k_entry:
                    logger.debug(f"[L2 Trap] IDLE -> ACTIVE_BEAR_TRAP (Spot RoC: {spot_roc:.2f}, Put RoC: {put_roc:.2f})")
                    self._state = DivergenceState.ACTIVE_BEAR_TRAP
                    self._exit_count = 0
            else:
                self._entry_count = max(0, self._entry_count - 1)

        elif self._state == DivergenceState.ACTIVE_BULL_TRAP:
            # Exit conditions
            if abs(spot_roc) < th_spot_exit or call_roc > th_opt_recover:
                self._exit_count += 1
                if self._exit_count >= k_exit:
                    logger.debug(f"[L2 Trap] ACTIVE_BULL_TRAP -> IDLE (Spot RoC: {spot_roc:.2f}, Call RoC: {call_roc:.2f})")
                    self._state = DivergenceState.IDLE
                    self._entry_count = 0
            # Rocket exit (option price surging)
            elif call_roc > settings.agent_b_th_opt_rocket_pct:
                logger.debug(f"[L2 Trap] ACTIVE_BULL_TRAP -> IDLE via ROCKET (Call RoC: {call_roc:.2f} > {settings.agent_b_th_opt_rocket_pct})")
                self._state = DivergenceState.IDLE
                self._entry_count = 0
            else:
                self._exit_count = 0

        elif self._state == DivergenceState.ACTIVE_BEAR_TRAP:
            if abs(spot_roc) < th_spot_exit or put_roc > th_opt_recover:
                self._exit_count += 1
                if self._exit_count >= k_exit:
                    logger.debug(f"[L2 Trap] ACTIVE_BEAR_TRAP -> IDLE (Spot RoC: {spot_roc:.2f}, Put RoC: {put_roc:.2f})")
                    self._state = DivergenceState.IDLE
                    self._entry_count = 0
            elif put_roc > settings.agent_b_th_opt_rocket_pct:
                logger.debug(f"[L2 Trap] ACTIVE_BEAR_TRAP -> IDLE via ROCKET (Put RoC: {put_roc:.2f} > {settings.agent_b_th_opt_rocket_pct})")
                self._state = DivergenceState.IDLE
                self._entry_count = 0
            else:
                self._exit_count = 0

        return self._state

    def _idle_result(self, now: datetime, snapshot: dict[str, Any]) -> AgentResult:
        """Return an IDLE result."""
        return AgentResult(
            agent=self.AGENT_ID,
            signal=DivergenceState.IDLE.value,
            as_of=now,
            data={
                "net_gex": None,
                "gamma_walls": {},
                "gamma_flip": False,
                "gamma_flip_level": None,
                "micro_structure": {},
            },
            summary="IDLE",
        )

    # Store last result for throttling
    _last_result: AgentResult | None = None

    def reset(self) -> None:
        """Reset agent state."""
        self._history.clear()
        self._state = DivergenceState.IDLE
        self._entry_count = 0
        self._exit_count = 0
        self._iv_tracker.reset()
        self._wall_tracker.reset()
        self._vanna_analyzer.reset()

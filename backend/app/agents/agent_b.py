"""Agent B1 — Options Structure / Trap Detection.

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

        # Greeks extractor
        self._greeks_extractor = GreeksExtractor()

        # Microstructure trackers (v2.0)
        self._iv_tracker = IVVelocityTracker()
        self._wall_tracker = WallMigrationTracker()
        self._vanna_analyzer = VannaFlowAnalyzer()

        # MTF trackers (Multi-Timeframe)
        self._iv_tracker_1m = IVVelocityTracker(window_seconds=settings.mtf_window_seconds_1min)
        self._iv_tracker_5m = IVVelocityTracker(window_seconds=settings.mtf_window_seconds_5min)
        self._iv_tracker_15m = IVVelocityTracker(window_seconds=settings.mtf_window_seconds_15min)

    def run(self, snapshot: dict[str, Any]) -> AgentResult:
        """Process market snapshot and detect traps.

        Args:
            snapshot: Market data dict with keys:
                spot, call_mark, put_mark, chain, volume, etc.
        """
        now = datetime.now(ZoneInfo("US/Eastern"))
        now_mono = time.monotonic()

        # Throttle
        elapsed = now_mono - self._last_run_time
        if elapsed < settings.agent_b_gamma_tick_interval:
            return self._last_result or self._idle_result(now, snapshot)
        self._last_run_time = now_mono

        spot = snapshot.get("spot")
        call_mark = snapshot.get("call_mark", 0) or 0
        put_mark = snapshot.get("put_mark", 0) or 0
        chain = snapshot.get("chain", [])

        if not spot or spot <= 0:
            return self._idle_result(now, snapshot)

        # 1. Greeks computation
        greeks = self._greeks_extractor.compute(chain, spot, as_of=now)

        # 2. Microstructure analysis
        micro = self._run_microstructure(
            spot=spot,
            atm_iv=greeks.get("atm_iv"),
            net_gex=greeks.get("net_gex"),
            call_wall=greeks.get("gamma_walls", {}).get("call_wall"),
            put_wall=greeks.get("gamma_walls", {}).get("put_wall"),
            call_wall_volume=0,
            put_wall_volume=0,
            sim_clock_mono=now_mono,
        )

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

        # Build result
        return AgentResult(
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
            },
            summary="; ".join(summary_parts) if summary_parts else "IDLE",
        )

    def _run_microstructure(
        self,
        *,
        spot: float,
        atm_iv: float | None,
        net_gex: float | None,
        call_wall: float | None,
        put_wall: float | None,
        call_wall_volume: int,
        put_wall_volume: int,
        sim_clock_mono: float | None = None,
    ) -> dict[str, Any]:
        """Run all microstructure trackers."""
        if not settings.agent_b1_v2_enabled:
            return {}

        # IV Velocity
        iv_result = self._iv_tracker.update(
            spot=spot, atm_iv=atm_iv, sim_clock_mono=sim_clock_mono
        )

        # Wall Migration
        wall_result = self._wall_tracker.update(
            call_wall=call_wall,
            put_wall=put_wall,
            call_wall_volume=call_wall_volume,
            put_wall_volume=put_wall_volume,
            sim_clock_mono=sim_clock_mono,
        )

        # Vanna Flow
        vanna_result = self._vanna_analyzer.update(
            spot=spot,
            atm_iv=atm_iv,
            net_gex=net_gex,
            spy_atm_iv=atm_iv,
            sim_clock_mono=sim_clock_mono,
        )

        # MTF (Multi-Timeframe) Consensus
        iv_1m = self._iv_tracker_1m.update(spot=spot, atm_iv=atm_iv, sim_clock_mono=sim_clock_mono)
        iv_5m = self._iv_tracker_5m.update(spot=spot, atm_iv=atm_iv, sim_clock_mono=sim_clock_mono)
        iv_15m = self._iv_tracker_15m.update(spot=spot, atm_iv=atm_iv, sim_clock_mono=sim_clock_mono)

        mtf_consensus = self._compute_mtf_consensus(iv_1m, iv_5m, iv_15m)

        return {
            "iv_velocity": iv_result.model_dump() if iv_result else None,
            "wall_migration": wall_result.model_dump() if wall_result else None,
            "vanna_flow_result": vanna_result.model_dump() if vanna_result else None,
            "mtf_consensus": mtf_consensus,
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
                    self._state = DivergenceState.ACTIVE_BULL_TRAP
                    self._exit_count = 0
            # Check for BEAR TRAP entry: Spot down + Put dying
            elif spot_roc < -th_spot_entry and put_roc < th_opt_fade:
                self._entry_count += 1
                if self._entry_count >= k_entry:
                    self._state = DivergenceState.ACTIVE_BEAR_TRAP
                    self._exit_count = 0
            else:
                self._entry_count = max(0, self._entry_count - 1)

        elif self._state == DivergenceState.ACTIVE_BULL_TRAP:
            # Exit conditions
            if abs(spot_roc) < th_spot_exit or call_roc > th_opt_recover:
                self._exit_count += 1
                if self._exit_count >= k_exit:
                    self._state = DivergenceState.IDLE
                    self._entry_count = 0
            # Rocket exit (option price surging)
            elif call_roc > settings.agent_b_th_opt_rocket_pct:
                self._state = DivergenceState.IDLE
                self._entry_count = 0
            else:
                self._exit_count = 0

        elif self._state == DivergenceState.ACTIVE_BEAR_TRAP:
            if abs(spot_roc) < th_spot_exit or put_roc > th_opt_recover:
                self._exit_count += 1
                if self._exit_count >= k_exit:
                    self._state = DivergenceState.IDLE
                    self._entry_count = 0
            elif put_roc > settings.agent_b_th_opt_rocket_pct:
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

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

from l2_decision.agents.base import AgentResult
from l2_decision.agents.base import AgentResult
from shared.config import settings


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

        # Greeks extractor (Legacy - state moving to L1)
        pass

    async def set_redis_client(self, client: Any) -> None:
        """Shared Redis client (Legacy - state moving to L1)."""
        pass

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

        # 1. Unified Extraction (Handles EnrichedSnapshot object or legacy dict)
        def _get_val(obj, key, default=None):
            if hasattr(obj, key): return getattr(obj, key, default)
            if isinstance(obj, dict): return obj.get(key, default)
            return default

        def _get_agg(obj, key, default=None):
            # Aggregates are nested in EnrichedSnapshot but flat in legacy dict
            if hasattr(obj, "aggregates"):
                return getattr(obj.aggregates, key, default)
            if isinstance(obj, dict):
                return obj.get(key, default)
            return default

        net_gex = _get_agg(snapshot, "net_gex", 0.0)
        atm_iv = _get_agg(snapshot, "atm_iv", 0.0)
        call_wall = _get_agg(snapshot, "call_wall", 0.0)
        put_wall = _get_agg(snapshot, "put_wall", 0.0)
        flip_level = _get_agg(snapshot, "flip_level", 0.0)
        net_vanna = _get_agg(snapshot, "net_vanna", 0.0)
        net_charm = _get_agg(snapshot, "net_charm", 0.0)
        spot = _get_val(snapshot, "spot", 0.0)

        # 2. Microstructure (Refactor: Pulling from L1 Snapshot)
        micro = _get_val(snapshot, "microstructure")
        if not micro:
             micro = snapshot.get("micro_structure", {}).get("micro_structure_state", {}) if isinstance(snapshot, dict) else {}

        # Map microstructure fields for AgentG compatibility
        m_dict = micro if isinstance(micro, dict) else {}
        if hasattr(micro, "iv_velocity"):
            m_dict = {
                "iv_velocity": micro.iv_velocity,
                "wall_migration": micro.wall_migration,
                "vanna_flow_result": micro.vanna_flow_result,
                "mtf_consensus": micro.mtf_consensus,
                "volume_imbalance": micro.volume_imbalance,
                "jump_detection": micro.jump_detection,
                "dealer_squeeze_alert": micro.dealer_squeeze_alert,
                "iv_confidence": micro.iv_confidence,
                "wall_confidence": micro.wall_confidence,
                "vanna_confidence": micro.vanna_confidence,
            }

        # Throttle Logic (Only for heavy Trap Detection)
        elapsed = now_mono - self._last_run_time
        if elapsed < settings.agent_b_gamma_tick_interval and self._last_result:
            self._micro_updated_at = now_mono
            sync_gap = now_mono - self._trap_updated_at
            updated_data = dict(self._last_result.data)
            
            updated_data.update({
                "micro_structure": {"micro_structure_state": m_dict},
                "iv_confidence": m_dict.get("iv_confidence", 0),
                "wall_confidence": m_dict.get("wall_confidence", 0),
                "vanna_confidence": m_dict.get("vanna_confidence", 0),
                "mtf_consensus": m_dict.get("mtf_consensus", {}),
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

        # PP-5 FIX: Record that a full trap recompute just ran (both rates in sync now).
        self._trap_updated_at = now_mono
        self._micro_updated_at = now_mono

        # Build result
        result = AgentResult(
            agent=self.AGENT_ID,
            signal=signal.value if isinstance(signal, DivergenceState) else str(signal),
            as_of=now,
            data={
                "net_gex": net_gex,
                "spy_atm_iv": atm_iv,
                "gamma_walls": {"call_wall": call_wall, "put_wall": put_wall},
                "gamma_flip_level": flip_level,
                "micro_structure": {
                    "micro_structure_state": m_dict,
                },
                "iv_confidence": m_dict.get("iv_confidence", 0),
                "wall_confidence": m_dict.get("wall_confidence", 0),
                "vanna_confidence": m_dict.get("vanna_confidence", 0),
                "gamma_profile": snapshot.get("gamma_profile", []),
                "per_strike_gex": snapshot.get("per_strike_gex", []),
                "top_active_options": chain,
                # PP-5 FIX: Dual-rate sync diagnostics (gap = 0 on full recompute)
                "trap_computed_at": self._trap_updated_at,
                "micro_computed_at": self._micro_updated_at,
                "trap_micro_sync_gap": 0.0,
            },
            summary="; ".join(summary_parts) if summary_parts else "IDLE",
        )
        
        self._last_result = result
        return result

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
        """Return an IDLE result.
        
        PP-6 FIX: Preserve market structure history during idle ticks to prevent UI flickering.
        BUG-5 FIX: Also preserve per_strike_gex and gamma_profile so DepthProfile
        does not flash blank when spot is temporarily unavailable.
        """
        last_data = getattr(self, '_last_result', None).data if getattr(self, '_last_result', None) else {}
        
        return AgentResult(
            agent=self.AGENT_ID,
            signal=DivergenceState.IDLE.value,
            as_of=now,
            data={
                "net_gex": last_data.get("net_gex"),
                "spy_atm_iv": last_data.get("spy_atm_iv"),
                "gamma_walls": last_data.get("gamma_walls", {}),
                "gamma_flip": last_data.get("gamma_flip", False),
                "gamma_flip_level": last_data.get("gamma_flip_level"),
                "micro_structure": last_data.get("micro_structure", {}),
                # Preserve Analysis fields
                "hv_analysis": last_data.get("hv_analysis"),
                "charm_analysis": last_data.get("charm_analysis"),
                "skew_analysis": last_data.get("skew_analysis"),
                "iv_confidence": last_data.get("iv_confidence"),
                "wall_confidence": last_data.get("wall_confidence"),
                "vanna_confidence": last_data.get("vanna_confidence"),
                "mtf_consensus": last_data.get("mtf_consensus"),
                # BUG-5 FIX: Preserve per_strike_gex + gamma_profile so DepthProfile
                # component does not flash blank on idle ticks (spot=None or empty chain).
                "per_strike_gex": last_data.get("per_strike_gex", []),
                "gamma_profile":  last_data.get("gamma_profile", []),
            },
            summary="IDLE (Stale Data Preserved)",
        )

    # Store last result for throttling
    _last_result: AgentResult | None = None

    def reset(self) -> None:
        """Reset agent state (Legacy - partial reset as trackers moved)."""
        self._history.clear()
        self._state = DivergenceState.IDLE
        self._entry_count = 0
        self._exit_count = 0

"""l2_decision.signals.trap_detector — Bull/Bear trap detection signal.

Extracted from backend/app/agents/agent_b.py (AgentB1._update_state).
State machine detects spot/option price divergence.

State machine:
    IDLE → ENTERING (k_entry consecutive confirming ticks) → ACTIVE
    ACTIVE → EXITING (k_exit consecutive non-confirming ticks) → IDLE

Changes vs legacy AgentB1:
    - Consumes FeatureVector (no snapshot dict)
    - YAML-configurable parameters (no settings.agent_b* references)
    - IV chaos gate: suppresses signals during extreme volatility
    - Returns normalized RawSignal with BULL_TRAP→BEARISH, BEAR_TRAP→BULLISH
      mapping for unified fusion consumption
"""

from __future__ import annotations

import math
from collections import deque
from datetime import datetime
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from l2_decision.events.decision_events import FeatureVector, RawSignal
from l2_decision.feature_store.registry import load_signal_config, get_param
from l2_decision.signals.base import SignalGeneratorBase

_ET = ZoneInfo("US/Eastern")


class _TrapState(str, Enum):
    IDLE = "IDLE"
    ENTERING_BULL = "ENTERING_BULL"
    ACTIVE_BULL = "ACTIVE_BULL"
    ENTERING_BEAR = "ENTERING_BEAR"
    ACTIVE_BEAR = "ACTIVE_BEAR"


class TrapDetector(SignalGeneratorBase):
    """Options structure divergence detector (Trap Machine).

    Signal semantics (for unified fusion):
        BULL TRAP detected → returns BEARISH (rally is fake)
        BEAR TRAP detected → returns BULLISH (drop is fake)
        No trap → returns NEUTRAL

    Consumes:
        spot_roc_1m     — spot 1-minute ROC
        atm_iv          — ATM IV for chaos gate
        bbo_imbalance_ewma  — optional confirming signal
    """

    name = "trap_detector"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None:
            config = load_signal_config("trap_detector")
        super().__init__(config)

        self._spot_entry: float = self._param("spot_entry_threshold", 0.002)
        self._opt_fade: float = self._param("opt_fade_threshold", -0.001)
        self._k_entry: int = int(self._param("k_entry", 3))
        self._k_exit: int = int(self._param("k_exit", 2))
        self._rocket_exit: float = self._param("rocket_exit_pct", 0.05)
        self._iv_chaos_threshold: float = self._param("iv_chaos_threshold", 0.60)
        self._conf_base: float = self._param("confidence_base", 0.70)
        self._conf_decay: float = self._param("confidence_decay_per_tick", 0.05)

        # State machine
        self._state: _TrapState = _TrapState.IDLE
        self._state_ticks: int = 0
        self._recent_roc: deque[float] = deque(maxlen=max(self._k_entry, self._k_exit) + 5)
        self._current_confidence: float = 0.0

        # Synthetic option ROC tracker (approximated from spot_roc sign flip)
        # In legacy: used actual call_mark/put_mark deque. Here approximated
        # from BBO divergence as proxy for option price fade.
        self._bbo_history: deque[float] = deque(maxlen=20)

    def generate(self, features: FeatureVector) -> RawSignal:
        """Detect bull/bear traps from feature vector."""
        try:
            spot_roc = features.get("spot_roc_1m", 0.0)
            atm_iv = features.get("atm_iv", 0.20)
            bbo = features.get("bbo_imbalance_ewma", 0.0)
        except Exception:
            return self._make_neutral()

        self._tick_count += 1

        # IV chaos gate: suppress during extreme volatility
        if math.isfinite(atm_iv) and atm_iv > self._iv_chaos_threshold:
            self._state = _TrapState.IDLE
            return self._make_neutral(metadata={"iv_chaos_gate": atm_iv})

        # Rocket mode: extreme spot move cancels bear trap
        if abs(spot_roc) > self._rocket_exit:
            if self._state == _TrapState.ACTIVE_BEAR:
                self._state = _TrapState.IDLE
            return self._make_neutral(metadata={"rocket_mode": spot_roc})

        self._recent_roc.append(spot_roc)
        self._bbo_history.append(bbo)

        # Proxy for option ROC: if spot is up but BBO is fading (net selling into call side)
        # → bullish divergence = bull trap candidate
        opt_fade_proxy = -bbo if spot_roc > 0 else bbo  # fade direction

        # State machine transitions
        if self._state == _TrapState.IDLE:
            if spot_roc > self._spot_entry and opt_fade_proxy < self._opt_fade:
                self._state = _TrapState.ENTERING_BULL
                self._state_ticks = 1
            elif spot_roc < -self._spot_entry and opt_fade_proxy < self._opt_fade:
                self._state = _TrapState.ENTERING_BEAR
                self._state_ticks = 1
            else:
                return self._make_neutral(metadata={"spot_roc": spot_roc})

        elif self._state == _TrapState.ENTERING_BULL:
            if spot_roc > self._spot_entry and opt_fade_proxy < self._opt_fade:
                self._state_ticks += 1
                if self._state_ticks >= self._k_entry:
                    self._state = _TrapState.ACTIVE_BULL
                    self._state_ticks = 0
                    self._current_confidence = self._conf_base
            else:
                self._state = _TrapState.IDLE
                self._state_ticks = 0

        elif self._state == _TrapState.ENTERING_BEAR:
            if spot_roc < -self._spot_entry and opt_fade_proxy < self._opt_fade:
                self._state_ticks += 1
                if self._state_ticks >= self._k_entry:
                    self._state = _TrapState.ACTIVE_BEAR
                    self._state_ticks = 0
                    self._current_confidence = self._conf_base
            else:
                self._state = _TrapState.IDLE
                self._state_ticks = 0

        elif self._state == _TrapState.ACTIVE_BULL:
            # Count exit ticks
            if spot_roc > self._spot_entry and opt_fade_proxy < self._opt_fade:
                self._state_ticks = 0
            else:
                self._state_ticks += 1
                self._current_confidence = max(0.0, self._current_confidence - self._conf_decay)
                if self._state_ticks >= self._k_exit:
                    self._state = _TrapState.IDLE
                    return self._make_neutral(metadata={"exiting_bull_trap": 1.0})

        elif self._state == _TrapState.ACTIVE_BEAR:
            if spot_roc < -self._spot_entry and opt_fade_proxy < self._opt_fade:
                self._state_ticks = 0
            else:
                self._state_ticks += 1
                self._current_confidence = max(0.0, self._current_confidence - self._conf_decay)
                if self._state_ticks >= self._k_exit:
                    self._state = _TrapState.IDLE
                    return self._make_neutral(metadata={"exiting_bear_trap": 1.0})

        # Emit signal based on current active state
        if self._state == _TrapState.ACTIVE_BULL:
            # Bull trap → underlying rally is fake → BEARISH signal
            return self._make_signal(
                direction="BEARISH",
                confidence=self._current_confidence,
                raw_value=-0.8,
                metadata={"trap_type": -1.0, "spot_roc": spot_roc, "bbo": bbo},
            )
        elif self._state == _TrapState.ACTIVE_BEAR:
            # Bear trap → underlying drop is fake → BULLISH signal
            return self._make_signal(
                direction="BULLISH",
                confidence=self._current_confidence,
                raw_value=0.8,
                metadata={"trap_type": 1.0, "spot_roc": spot_roc, "bbo": bbo},
            )
        else:
            return self._make_neutral(metadata={"spot_roc": spot_roc})

    def reset(self) -> None:
        """Reset state machine to IDLE."""
        super().reset()
        self._state = _TrapState.IDLE
        self._state_ticks = 0
        self._recent_roc.clear()
        self._bbo_history.clear()
        self._current_confidence = 0.0

    @property
    def current_state(self) -> str:
        """Read-only state for monitoring."""
        return self._state.value

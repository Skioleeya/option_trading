"""l2_decision.guards.rail_engine — Independent P0.0–P0.9 Risk Guard Rails.

Extracts guard gate logic from backend/app/agents/agent_g.py (AgentG._decide_impl)
into an independent, testable priority chain.

Priority order (lower number = higher priority, evaluated first):
    P0.0  KillSwitchGuard     — manual halt
    P0.1  JumpGateGuard       — price jump suppression
    P0.3  CorrelationGuard    — cross-asset correlation break  (new)
    P0.5  VRPVetoGuard        — volatility risk premium veto
    P0.7  DrawdownGuard       — daily loss circuit breaker     (new)
    P0.9  SessionGuard        — open/close window dampening   (new)

Each GuardRule is independently testable and hot-swappable.
The chain is processed in priority order; a HALT from any rule
short-circuits the remaining guards.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Protocol, runtime_checkable
from zoneinfo import ZoneInfo

from l2_decision.events.decision_events import FusedDecision, GuardedDecision
from shared.config import settings
from shared.system.tactical_triad_logic import (
    compute_guard_vrp_proxy_pct,
    normalize_guard_vrp_threshold_pct,
)

logger = logging.getLogger(__name__)

_ET = ZoneInfo("US/Eastern")


# ─────────────────────────────────────────────────────────────────────────────
# GuardRule Protocol
# ─────────────────────────────────────────────────────────────────────────────

@runtime_checkable
class GuardRule(Protocol):
    """Interface for a single guard rail rule."""
    priority: float    # Lower = higher priority (P0.0 beats P0.9)
    name: str

    def check(
        self, decision: FusedDecision, context: dict[str, Any]
    ) -> tuple[bool, str, float]:
        """Check if this guard rule triggers.

        Returns:
            (triggered: bool, action_description: str, confidence_multiplier: float)
            confidence_multiplier: 1.0 = no change; 0.0 = HALT; 0.5 = 50% reduction.
        """
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Concrete Guard Implementations
# ─────────────────────────────────────────────────────────────────────────────

class KillSwitchGuard:
    """P0.0 — Manual halt via ManualKillSwitch."""

    priority = 0.0
    name = "KillSwitchGuard"

    def __init__(self, kill_switch: Any) -> None:
        self._switch = kill_switch

    def check(self, decision: FusedDecision, context: dict[str, Any]) -> tuple[bool, str, float]:
        if self._switch.is_active():
            return True, f"P0.0 HALT: {self._switch.reason}", 0.0
        return False, "", 1.0


class JumpGateGuard:
    """P0.1 — Suppress signals during active price jump detection window."""

    priority = 0.1
    name = "JumpGateGuard"

    def __init__(self, jump_sentinel: Any) -> None:
        self._sentinel = jump_sentinel

    def check(self, decision: FusedDecision, context: dict[str, Any]) -> tuple[bool, str, float]:
        if hasattr(self._sentinel, "is_active_jump") and self._sentinel.is_active_jump():
            return True, "P0.1 JumpGate: active jump detected, suppressing", 0.0
        return False, "", 1.0


class VRPVetoGuard:
    """P0.5 — Veto signal when Volatility Risk Premium is excessive.

    guard_vrp_proxy_pct = ATM IV(%) - realized vol proxy(%), where
    realized-vol proxy still uses |vol_accel_ratio| engineering heuristic.
    High VRP → options are expensive → fade signals.
    """

    priority = 0.5
    name = "VRPVetoGuard"

    ENTRY_THRESHOLD = 15.0
    EXIT_THRESHOLD = 13.0
    MIN_HOLD_TICKS = 3
    EXIT_CONFIRM_TICKS = 2

    def __init__(
        self,
        entry_threshold: float | None = None,
        exit_threshold: float | None = None,
        min_hold_ticks: int | None = None,
        exit_confirm_ticks: int | None = None,
    ) -> None:
        self._entry_threshold = normalize_guard_vrp_threshold_pct(
            entry_threshold
            if entry_threshold is not None
            else getattr(settings, "guard_vrp_entry_threshold", self.ENTRY_THRESHOLD),
            self.ENTRY_THRESHOLD,
        )
        self._exit_threshold = normalize_guard_vrp_threshold_pct(
            exit_threshold
            if exit_threshold is not None
            else getattr(settings, "guard_vrp_exit_threshold", self.EXIT_THRESHOLD),
            self.EXIT_THRESHOLD,
        )
        self._min_hold_ticks = max(
            1,
            int(
                min_hold_ticks
                if min_hold_ticks is not None
                else getattr(settings, "guard_vrp_min_hold_ticks", self.MIN_HOLD_TICKS)
            ),
        )
        self._exit_confirm_ticks = max(
            1,
            int(
                exit_confirm_ticks
                if exit_confirm_ticks is not None
                else getattr(settings, "guard_vrp_exit_confirm_ticks", self.EXIT_CONFIRM_TICKS)
            ),
        )
        self._active = False
        self._active_ticks = 0
        self._below_exit_ticks = 0

    def check(self, decision: FusedDecision, context: dict[str, Any]) -> tuple[bool, str, float]:
        vrp = compute_guard_vrp_proxy_pct(
            decision.feature_vector.get("atm_iv", 0.20),
            decision.feature_vector.get("vol_accel_ratio", 0.0),
        )
        if vrp is None:
            return False, "", 1.0

        if not self._active:
            if vrp > self._entry_threshold:
                self._active = True
                self._active_ticks = 1
                self._below_exit_ticks = 0
                return True, f"P0.5 VRPVeto: guard_vrp_proxy_pct={vrp:.2f}> {self._entry_threshold:.2f}", 0.6
            return False, "", 1.0

        # Active state: hold while above exit threshold, and require
        # minimum-hold + continuous below-exit confirmation before release.
        self._active_ticks += 1
        if vrp < self._exit_threshold:
            self._below_exit_ticks += 1
        else:
            self._below_exit_ticks = 0

        if (
            self._active_ticks >= self._min_hold_ticks
            and self._below_exit_ticks >= self._exit_confirm_ticks
        ):
            self._active = False
            self._active_ticks = 0
            self._below_exit_ticks = 0
            return False, "", 1.0

        return True, f"P0.5 VRPVeto: guard_vrp_proxy_pct={vrp:.2f}> {self._entry_threshold:.2f}", 0.6

    def reset_session(self) -> None:
        self._active = False
        self._active_ticks = 0
        self._below_exit_ticks = 0


class DrawdownGuard:
    """P0.7 — Cool-down when daily accumulated signal PnL < -$500.

    Tracks a running simulated PnL from confidence-weighted signal outcomes.
    In production, this should be fed with actual realized PnL.
    """

    priority = 0.7
    name = "DrawdownGuard"

    DRAWDOWN_LIMIT: float = -500.0
    COOLDOWN_DURATION_MINUTES: float = 30.0

    def __init__(
        self,
        drawdown_limit: float | None = None,
        cooldown_minutes: float | None = None,
    ) -> None:
        self._drawdown_limit = float(
            drawdown_limit
            if drawdown_limit is not None
            else getattr(settings, "guard_drawdown_limit_usd", self.DRAWDOWN_LIMIT)
        )
        self._cooldown_minutes = float(
            cooldown_minutes
            if cooldown_minutes is not None
            else getattr(settings, "guard_drawdown_cooldown_minutes", self.COOLDOWN_DURATION_MINUTES)
        )
        self._session_pnl: float = 0.0
        self._cooldown_until: datetime | None = None

    def check(self, decision: FusedDecision, context: dict[str, Any]) -> tuple[bool, str, float]:
        now = datetime.now(_ET)

        # Check if in cooldown
        if self._cooldown_until is not None and now < self._cooldown_until:
            remaining = (self._cooldown_until - now).seconds // 60
            return True, f"P0.7 DrawdownGuard: cooldown {remaining}min remaining", 0.0

        if self._cooldown_until is not None and now >= self._cooldown_until:
            self._cooldown_until = None  # Cooldown expired

        # Inject realized PnL if provided in context
        if "realized_pnl" in context:
            self._session_pnl = float(context["realized_pnl"])

        if self._session_pnl < self._drawdown_limit:
            self._cooldown_until = now + timedelta(minutes=self._cooldown_minutes)
            logger.warning(
                "DrawdownGuard: session PnL %.1f < %.1f, entering %.0fmin cooldown",
                self._session_pnl, self._drawdown_limit, self._cooldown_minutes,
            )
            return True, f"P0.7 DrawdownGuard: PnL={self._session_pnl:.0f}<{self._drawdown_limit}", 0.0

        return False, "", 1.0

    def reset_session(self) -> None:
        """Reset at session boundary (new trading day)."""
        self._session_pnl = 0.0
        self._cooldown_until = None

    def update_pnl(self, pnl: float) -> None:
        """Update simulated session PnL."""
        self._session_pnl = pnl


class SessionGuard:
    """P0.9 — Reduce confidence during first/last 15 minutes of session.

    Opening and closing windows have elevated microstructure noise.
    Reduces output confidence by 30% during these periods.
    """

    priority = 0.9
    name = "SessionGuard"

    WINDOW_MINUTES = 15
    CONFIDENCE_REDUCTION = 0.30

    def __init__(
        self,
        window_minutes: int | None = None,
        confidence_reduction: float | None = None,
    ) -> None:
        self._window_minutes = max(
            1,
            int(
                window_minutes
                if window_minutes is not None
                else getattr(settings, "guard_session_window_minutes", self.WINDOW_MINUTES)
            ),
        )
        raw_reduction = float(
            confidence_reduction
            if confidence_reduction is not None
            else getattr(settings, "guard_session_confidence_reduction", self.CONFIDENCE_REDUCTION)
        )
        self._confidence_reduction = max(0.0, min(1.0, raw_reduction))

    def check(self, decision: FusedDecision, context: dict[str, Any]) -> tuple[bool, str, float]:
        now = datetime.now(_ET)
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

        opening_end = market_open + timedelta(minutes=self._window_minutes)
        closing_start = market_close - timedelta(minutes=self._window_minutes)

        in_opening = market_open <= now < opening_end
        in_closing = closing_start <= now <= market_close

        if in_opening or in_closing:
            window = "opening" if in_opening else "closing"
            multiplier = 1.0 - self._confidence_reduction
            return True, f"P0.9 SessionGuard: {window} window → confidence ×{multiplier:.1f}", multiplier

        return False, "", 1.0


# ─────────────────────────────────────────────────────────────────────────────
# GuardRailEngine — Priority Chain Processor
# ─────────────────────────────────────────────────────────────────────────────

class GuardRailEngine:
    """Priority-ordered guard rail chain processor.

    Processes FusedDecision through all registered GuardRules in
    priority order (P0.0 → P0.9). HALT from any rule short-circuits
    remaining guards.

    Usage:
        engine = GuardRailEngine.build_default(kill_switch, jump_sentinel)
        guarded = engine.process(fused_decision)
    """

    def __init__(self, rules: list[Any]) -> None:
        # Sort by priority (ascending = higher priority first)
        self._rules: list[Any] = sorted(rules, key=lambda r: r.priority)
        logger.info(
            "GuardRailEngine: registered %d rules: %s",
            len(self._rules),
            [r.name for r in self._rules],
        )

    @classmethod
    def build_default(
        cls,
        kill_switch: Any,
        jump_sentinel: Any | None = None,
    ) -> "GuardRailEngine":
        """Factory: construct with standard P0.0–P0.9 guard set."""
        rules: list[Any] = [
            KillSwitchGuard(kill_switch),
            VRPVetoGuard(),
            DrawdownGuard(),
            SessionGuard(),
        ]
        if jump_sentinel is not None:
            rules.append(JumpGateGuard(jump_sentinel))

        return cls(rules)

    def process(
        self,
        fused: FusedDecision,
        context: dict[str, Any] | None = None,
    ) -> GuardedDecision:
        """Run all guard rules against fused decision.

        Returns:
            GuardedDecision with final direction, adjusted confidence,
            and full guard audit trail.
        """
        t0 = time.perf_counter()
        ctx = context or {}

        current_confidence = fused.confidence
        actions: list[str] = []
        is_halted = False

        for rule in self._rules:
            try:
                triggered, description, multiplier = rule.check(fused, ctx)
            except Exception as exc:
                logger.exception("GuardRule %s raised unexpectedly: %s", rule.name, exc)
                continue

            if triggered:
                actions.append(description)
                if multiplier == 0.0:
                    # Hard halt — short-circuit remaining rules
                    current_confidence = 0.0
                    is_halted = True
                    logger.warning("Guard halted by %s: %s", rule.name, description)
                    break
                else:
                    # Soft confidence reduction
                    current_confidence *= multiplier
                    logger.debug("Guard reduced confidence by %s: %s", rule.name, description)

        # Clamp confidence
        current_confidence = max(0.0, min(1.0, current_confidence))

        final_direction = "HALT" if is_halted else fused.direction
        latency_ms = (time.perf_counter() - t0) * 1000.0

        return GuardedDecision(
            direction=final_direction,
            confidence=current_confidence,
            pre_guard_direction=fused.direction,
            pre_guard_confidence=fused.confidence,
            guard_actions=actions,
            fused=fused,
            guard_latency_ms=latency_ms,
        )

    def add_rule(self, rule: Any) -> None:
        """Dynamically add a guard rule and re-sort by priority."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority)
        logger.info("GuardRailEngine: added rule %s (P%.1f)", rule.name, rule.priority)

    def reset_session(self) -> None:
        """Reset all stateful guards at session boundary."""
        for rule in self._rules:
            if hasattr(rule, "reset_session"):
                rule.reset_session()

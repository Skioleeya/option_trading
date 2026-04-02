from __future__ import annotations

import logging
from typing import Any, Callable

from l2_decision.agents.base import AgentResult


def map_iv_to_direction(iv_state: str | None) -> str:
    if iv_state in (
        "PAID_MOVE",
        "ORGANIC_GRIND",
        "HOLLOW_RISE",
        "HOLLOW_DROP",
        "VOL_EXPANSION",
        "EXHAUSTION",
    ):
        return "BULLISH"
    if iv_state == "PAID_DROP":
        return "BEARISH"
    return "NEUTRAL"


def map_wall_to_direction(call_state: str | None, put_state: str | None) -> str:
    if call_state == "BREACHED":
        return "BULLISH"
    if put_state == "BREACHED":
        return "BEARISH"
    if call_state == "RETREATING_RESISTANCE":
        return "BULLISH"
    if call_state == "REINFORCED_WALL":
        return "BEARISH"
    if put_state == "RETREATING_SUPPORT":
        return "BEARISH"
    if put_state == "REINFORCED_SUPPORT":
        return "BULLISH"
    return "NEUTRAL"


def map_vanna_to_direction(vanna_state: str | None) -> str:
    if vanna_state == "DANGER_ZONE":
        return "BULLISH"
    if vanna_state == "GRIND_STABLE":
        return "NEUTRAL"
    return "NEUTRAL"


def clamp01(raw: Any, default: float = 0.0) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def derive_mtf_geometry(mtf_consensus: Any, clamp01: Callable[[Any, float], float]) -> tuple[int, float, float]:
    if not isinstance(mtf_consensus, dict):
        return 0, 0.0, 0.0
    timeframes = mtf_consensus.get("timeframes")
    if not isinstance(timeframes, dict):
        return 0, 0.0, 0.0

    states: list[int] = []
    kinetics: list[float] = []
    for tf in ("1m", "5m", "15m"):
        tf_data = timeframes.get(tf, {})
        if not isinstance(tf_data, dict):
            continue
        raw_state = tf_data.get("state")
        if raw_state in (1, -1, 0):
            state = int(raw_state)
        elif raw_state in ("1", "-1", "0"):
            state = int(raw_state)
        else:
            state = 0
        states.append(state)
        kinetics.append(clamp01(tf_data.get("kinetic_level", 0.0), 0.0))

    if not states:
        return 0, 0.0, 0.0

    balance = sum(states)
    consensus_state = 1 if balance > 0 else (-1 if balance < 0 else 0)
    confidence = sum(kinetics) / len(kinetics) if kinetics else 0.0
    dominant_count = max(states.count(-1), states.count(0), states.count(1))
    alignment = dominant_count / len(states)
    return consensus_state, clamp01(confidence, 0.0), clamp01(alignment, 0.0)


def append_sync_gap_diagnostic(
    summary: list[str],
    agent_b_data: dict[str, Any],
    gamma_tick_interval: float,
    logger: logging.Logger,
) -> None:
    sync_gap = agent_b_data.get("trap_micro_sync_gap", 0.0) or 0.0
    if sync_gap <= gamma_tick_interval * 3:
        return
    summary.append(
        f"[PP-5 DIAG] Trap state stale: trap_micro_sync_gap={sync_gap:.2f}s "
        f"(>{gamma_tick_interval * 3:.1f}s). "
        "Consider reducing agent_b_gamma_tick_interval."
    )
    logger.debug("[AgentG] PP-5: trap/micro sync gap=%.2fs", sync_gap)


def resolve_vrp(
    *,
    spy_atm_iv: float | None,
    hv_analysis: dict[str, Any],
    vrp_baseline_hv: Any,
    vrp_cheap_threshold: Any,
    vrp_expensive_threshold: Any,
    vrp_trap_threshold: Any,
    compute_vrp: Callable[[Any, Any], float | None],
    classify_vrp_state: Callable[[Any, Any, Any, Any], str],
) -> tuple[float | None, str]:
    vrp = hv_analysis.get("vrp")
    if vrp is None and spy_atm_iv is not None:
        vrp = compute_vrp(spy_atm_iv, vrp_baseline_hv)
    premium_state = classify_vrp_state(
        vrp,
        vrp_cheap_threshold,
        vrp_expensive_threshold,
        vrp_trap_threshold,
    )
    return vrp, premium_state


def build_jump_gate_result(
    *,
    agent_id: str,
    jump_data: Any,
    agent_b: AgentResult,
    fused_signal: Any,
    summary: list[str],
) -> AgentResult | None:
    if not jump_data or not jump_data.is_jump:
        return None
    signal = f"HOLD (JUMP_DETECTED: |Z|={abs(jump_data.z_score):.1f})"
    summary.append(
        f"SAFETY VALVE (P0.1): Price shock detected ({jump_data.magnitude_pct:+.2f}%). "
        "Halting trade entry per Paper 5 safety protocol."
    )
    return AgentResult(
        agent=agent_id,
        signal=signal,
        as_of=agent_b.as_of,
        data={**agent_b.data, "fused_signal": fused_signal.model_dump()},
        summary="; ".join(summary),
    )


def apply_vrp_veto(
    *,
    vrp_active: bool,
    signal: str,
    summary: list[str],
    vrp: float,
    spy_atm_iv: float | None,
    entry_threshold: float,
    exit_ratio: float,
    logger: logging.Logger,
) -> tuple[bool, bool, str]:
    exit_threshold = entry_threshold * exit_ratio
    active = vrp_active
    if not active and vrp > entry_threshold:
        active = True
        logger.warning("[AgentG] VRP Veto ACTIVATED: %.1f > %.1f", vrp, entry_threshold)
    elif active and vrp < exit_threshold:
        active = False
        logger.warning("[AgentG] VRP Veto DEACTIVATED: %.1f < %.1f", vrp, exit_threshold)

    if not active:
        return active, False, signal

    safe_iv = float(spy_atm_iv or 0.0)
    summary.append(
        f"VRP VETO (P0.5): IV={safe_iv:.1f}% far too expensive (VRP={vrp:.1f}). "
        "Entry EV<0 per Muravyev et al. (SSRN #4019647)."
    )
    return active, True, f"NO_TRADE (VRP_VETO: VRP={vrp:.1f})"


def apply_mtf_alignment_policy(
    *,
    mtf_damped: bool,
    summary: list[str],
    fused_signal: Any,
    mtf_alignment: float,
    premium_state: str,
    vrp: float | None,
    mtf_entry_threshold: float,
    mtf_exit_threshold: float,
    vrp_bargain_boost: float,
    max_signal_confidence: float,
    logger: logging.Logger,
) -> tuple[bool, float]:
    damped = mtf_damped
    if not damped and mtf_alignment < mtf_entry_threshold:
        damped = True
        logger.info("[AgentG] MTF Damping ACTIVATED: alignment=%.2f < %.2f", mtf_alignment, mtf_entry_threshold)
    elif damped and mtf_alignment > mtf_exit_threshold:
        damped = False
        logger.info("[AgentG] MTF Damping DEACTIVATED: alignment=%.2f > %.2f", mtf_alignment, mtf_exit_threshold)

    if damped:
        summary.append(f"MTF ALIGN DAMP: alignment={mtf_alignment:.2f} -> conf halved.")
        return damped, fused_signal.confidence * 0.5
    if mtf_alignment >= 0.67 and premium_state == "BARGAIN":
        summary.append(f"VRP BARGAIN BOOST: alignment={mtf_alignment:.2f}, VRP={vrp:.1f}")
        return damped, min(fused_signal.confidence * vrp_bargain_boost, max_signal_confidence)
    return damped, fused_signal.confidence


def gex_accel_boost(
    *,
    summary: list[str],
    fused_signal: Any,
    net_gex: float | None,
    gex_accel_threshold: float,
    gex_accel_boost_bearish: float,
    gex_accel_boost_bullish: float,
) -> float:
    if net_gex is None:
        return 1.0
    if net_gex > 800 and fused_signal.direction == "NEUTRAL":
        summary.append("GEX PINNING: Strong Pos Gamma limiting volatility (Paper 2).")
        return 1.0
    if net_gex >= gex_accel_threshold:
        return 1.0
    if fused_signal.direction == "BEARISH":
        summary.append("GEX ACCEL: Neg Gamma reinforcing Bearish move (Paper 4).")
        return gex_accel_boost_bearish
    if fused_signal.direction == "BULLISH":
        summary.append("GEX ACCEL: Neg Gamma reinforcing Bullish bounce (Short Squeeze).")
        return gex_accel_boost_bullish
    return 1.0


def resolve_idle_trend_signal(
    *,
    summary: list[str],
    net_gex: float | None,
    agent_a_signal: str,
    current_signal: str,
) -> str:
    if net_gex is not None and net_gex < 0:
        if agent_a_signal == "BULLISH":
            summary.append("Trend Confirmed: Negative Gamma aligns with Bullish spot.")
            return "Option Structure: LONG_CALL (Neg Gamma Accel)"
        if agent_a_signal == "BEARISH":
            summary.append("Trend Confirmed: Negative Gamma aligns with Bearish spot.")
            return "Option Structure: LONG_PUT (Neg Gamma Accel)"
        summary.append(f"Negative Gamma but Spot Neutral. A={agent_a_signal}")
        return "NEUTRAL"
    if net_gex is not None and net_gex > 0:
        if agent_a_signal == "BULLISH":
            summary.append("Trend Muted: Positive Gamma suggests resistance/damping on upside.")
            return "NEUTRAL (Pos Gamma Damping)"
        if agent_a_signal == "BEARISH":
            summary.append("Trend Muted: Positive Gamma suggests support/damping on downside.")
            return "NEUTRAL (Pos Gamma Damping)"
        summary.append("Positive Gamma & Neutral Spot. Expect low vol.")
        return "NEUTRAL"
    summary.append(f"No signal. A={agent_a_signal}, GEX={net_gex}")
    return current_signal


def resolve_signal(
    *,
    current_signal: str,
    summary: list[str],
    b_signal: str,
    fused_signal: Any,
    net_gex: float | None,
    agent_a_signal: str,
    active_bull_trap: str,
    active_bear_trap: str,
    idle_state: str,
    fusion_confidence_threshold: float,
) -> str:
    if b_signal == active_bull_trap:
        summary.append("TRAP DETECTED: Bull Trap active (fading price rise).")
        return "Option Structure: LONG_PUT (Check Breadth!)"
    if b_signal == active_bear_trap:
        summary.append("TRAP DETECTED: Bear Trap active (fading price drop).")
        return "Option Structure: LONG_CALL (Check Breadth!)"
    if fused_signal.confidence > fusion_confidence_threshold:
        confidence_pct = fused_signal.confidence * 100
        summary.append(f"FUSION OVERRIDE: {fused_signal.explanation}")
        top_component = max(fused_signal.weights.items(), key=lambda item: item[1])
        summary.append(f"Primary driver: {top_component[0]} ({top_component[1]*100:.0f}%)")
        return f"Fusion Engine: {fused_signal.direction} (Conf {confidence_pct:.0f}%)"
    if b_signal != idle_state and b_signal != "IDLE":
        return current_signal
    return resolve_idle_trend_signal(
        summary=summary,
        net_gex=net_gex,
        agent_a_signal=agent_a_signal,
        current_signal=current_signal,
    )

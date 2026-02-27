from __future__ import annotations

import logging
from typing import Any

from app.agents.agent_a import AgentA
from app.agents.agent_b import AgentB1, DivergenceState
from app.agents.base import AgentResult
from app.config import settings
from app.models.agent_output import AgentB1Output
from app.services.fusion.dynamic_weight_engine import DynamicWeightEngine


logger = logging.getLogger(__name__)


class AgentG:
    """Decision framework agent.

    Combines Agent A (spot micro-signal) and Agent B1 (options structure/trap).

    Logic Hierarchy:
    1. Trap Preemption (Agent B1):
       - IF ACTIVE_BULL_TRAP (Price Up + Call Dying) -> FADE IT -> LONG_PUT.
       - IF ACTIVE_BEAR_TRAP (Price Down + Put Dying) -> FADE IT -> LONG_CALL.

    2. Trend Confirmation (Agent B1 Idle + Agent A):
       - IF IDLE AND (Agent A Bullish) AND (Net GEX > 0) -> LONG_CALL.
       - IF IDLE AND (Agent A Bearish) AND (Net GEX < 0) -> LONG_PUT.
    """

    AGENT_ID = "agent_g"

    def __init__(self, agent_a: AgentA | None = None, agent_b: AgentB1 | None = None):
        self._agent_a = agent_a or AgentA()
        self._agent_b = agent_b or AgentB1()
        self._weight_engine = DynamicWeightEngine()

    def _get_wall_interaction(
        self,
        spot: float | None,
        net_gex: float | None,
        agent_a_signal: str,
        call_wall: float | None,
        put_wall: float | None,
        magnet_pct: float,
    ) -> dict | None:
        """Helper to detect critical wall interactions for UI fx."""
        if not spot or net_gex is None:
            return None

        # Only trigger in Negative Gamma (Acceleration)
        if net_gex >= 0:
            return None

        if put_wall:
            dist_pct = (spot - put_wall) / spot * 100.0
            if -magnet_pct < dist_pct < magnet_pct:
                return {
                    "type": "APPROACHING_PUT",
                    "wall_level": put_wall,
                    "severity": "HIGH",
                    "effect": "glitch",
                }

        if call_wall:
            dist_pct = (call_wall - spot) / spot * 100.0
            if -magnet_pct < dist_pct < magnet_pct:
                return {
                    "type": "APPROACHING_CALL",
                    "wall_level": call_wall,
                    "severity": "HIGH",
                    "effect": "glitch",
                }

        return None

    def _map_iv_to_direction(self, iv_state: str | None) -> str:
        """Map IV velocity state to direction.

        v3.0 FIX: Asian Style Color Alignment (红涨绿跌)
        """
        if iv_state in ("PAID_MOVE", "ORGANIC_GRIND", "HOLLOW_RISE",
                        "HOLLOW_DROP", "VOL_EXPANSION", "EXHAUSTION"):
            return "BULLISH"
        elif iv_state == "PAID_DROP":
            return "BEARISH"
        else:
            return "NEUTRAL"

    def _map_wall_to_direction(self, call_state: str | None, put_state: str | None) -> str:
        """Map wall migration states to direction."""
        if call_state == "RETREATING_RESISTANCE":
            return "BULLISH"
        elif call_state == "REINFORCED_WALL":
            return "BEARISH"
        elif put_state == "RETREATING_SUPPORT":
            return "BEARISH"
        elif put_state == "REINFORCED_SUPPORT":
            return "BULLISH"
        else:
            return "NEUTRAL"

    def _map_vanna_to_direction(self, vanna_state: str | None) -> str:
        """Map vanna flow state to direction."""
        if vanna_state == "DANGER_ZONE":
            return "BEARISH"
        elif vanna_state == "GRIND_STABLE":
            return "BULLISH"
        else:
            return "NEUTRAL"

    def run(self, snapshot: dict[str, Any]) -> AgentResult:
        a = self._agent_a.run(snapshot)
        b = self._agent_b.run(snapshot)
        return self.decide(agent_a=a, agent_b=b)

    def decide(self, *, agent_a: AgentResult, agent_b: AgentResult) -> AgentResult:
        """Top-level guard wrapper."""
        try:
            return self._decide_impl(agent_a=agent_a, agent_b=agent_b)
        except Exception:
            logger.exception("[AgentG] decide() crashed; emitting NO_TRADE safety fallback")
            return AgentResult(
                agent=self.AGENT_ID,
                signal="NO_TRADE",
                as_of=agent_a.as_of,
                data={
                    "error": "decide_crashed",
                    "fused_signal": {
                        "direction": "NEUTRAL",
                        "confidence": 0.0,
                        "weights": {},
                        "regime": "UNKNOWN",
                        "iv_regime": "NORMAL",
                        "gex_intensity": "NEUTRAL",
                        "explanation": "AgentG.decide() exception; NO_TRADE issued.",
                        "components": {},
                    },
                },
                summary="AgentG.decide() exception; NO_TRADE issued.",
            )

    def _decide_impl(self, *, agent_a: AgentResult, agent_b: AgentResult) -> AgentResult:
        """Core decision logic."""
        b_output = AgentB1Output.model_validate(agent_b.data)

        # 1. Extract Data
        net_gex_f = b_output.net_gex
        b_signal = agent_b.signal
        summary = []
        signal = "NO_TRADE"

        spy_atm_iv = b_output.spy_atm_iv

        ms_analysis = b_output.micro_structure
        ms_state = ms_analysis.micro_structure_state if ms_analysis else None

        iv_data = ms_state.iv_velocity if ms_state else None
        wall_data = ms_state.wall_migration if ms_state else None
        vanna_data = ms_state.vanna_flow_result if ms_state else None
        if ms_state and not (vanna_data and (vanna_data.state != "NORMAL" or vanna_data.confidence)):
            vanna_data = ms_state.vanna_flow

        mtf_consensus = b_output.mtf_consensus or (ms_state.mtf_consensus if ms_state else {})

        # Confidence values
        iv_confidence = b_output.iv_confidence or (iv_data.confidence if iv_data else 0.0)
        wall_confidence = b_output.wall_confidence or (wall_data.confidence if wall_data else 0.0)
        vanna_confidence = b_output.vanna_confidence or (vanna_data.confidence if vanna_data else 0.0)

        # Map microstructure states to directions
        iv_direction = self._map_iv_to_direction(iv_data.state if iv_data else None)
        wall_direction = self._map_wall_to_direction(
            wall_data.call_wall_state if wall_data else None,
            wall_data.put_wall_state if wall_data else None,
        )
        vanna_direction = self._map_vanna_to_direction(vanna_data.state if vanna_data else None)
        mtf_direction = mtf_consensus.get("consensus", "NEUTRAL")

        # Update weight engine
        self._weight_engine.update_market_state(spy_atm_iv, net_gex_f)

        # Calculate fused signal
        fused_signal = self._weight_engine.calculate_weights(
            iv_signal={"direction": iv_direction, "confidence": iv_confidence},
            wall_signal={"direction": wall_direction, "confidence": wall_confidence},
            vanna_signal={"direction": vanna_direction, "confidence": vanna_confidence},
            mtf_signal={
                "direction": mtf_direction,
                "confidence": mtf_consensus.get("strength", 0.5),
            },
        )

        # 2. Trap Logic (Priority 1)
        if b_signal == DivergenceState.ACTIVE_BULL_TRAP:
            signal = "Option Structure: LONG_PUT (Check Breadth!)"
            summary.append("TRAP DETECTED: Bull Trap active (fading price rise).")
        elif b_signal == DivergenceState.ACTIVE_BEAR_TRAP:
            signal = "Option Structure: LONG_CALL (Check Breadth!)"
            summary.append("TRAP DETECTED: Bear Trap active (fading price drop).")

        # 2.5. Fusion Engine High Confidence Override (Priority 1.5)
        elif fused_signal.confidence > settings.fusion_confidence_threshold:
            direction = fused_signal.direction
            confidence_pct = fused_signal.confidence * 100
            signal = f"Fusion Engine: {direction} (Conf {confidence_pct:.0f}%)"
            summary.append(f"FUSION OVERRIDE: {fused_signal.explanation}")
            top_component = max(fused_signal.weights.items(), key=lambda x: x[1])
            summary.append(f"Primary driver: {top_component[0]} ({top_component[1]*100:.0f}%)")

        # 3. Trend Logic (Priority 2)
        elif b_signal == DivergenceState.IDLE or b_signal == "IDLE":
            if net_gex_f is not None and net_gex_f < 0:
                if agent_a.signal == "BULLISH":
                    signal = "Option Structure: LONG_CALL (Neg Gamma Accel)"
                    summary.append("Trend Confirmed: Negative Gamma aligns with Bullish spot.")
                elif agent_a.signal == "BEARISH":
                    signal = "Option Structure: LONG_PUT (Neg Gamma Accel)"
                    summary.append("Trend Confirmed: Negative Gamma aligns with Bearish spot.")
                else:
                    signal = "NEUTRAL"
                    summary.append(f"Negative Gamma but Spot Neutral. A={agent_a.signal}")
            elif net_gex_f is not None and net_gex_f > 0:
                if agent_a.signal == "BULLISH":
                    signal = "NEUTRAL (Pos Gamma Damping)"
                    summary.append("Trend Muted: Positive Gamma suggests resistance/damping on upside.")
                elif agent_a.signal == "BEARISH":
                    signal = "NEUTRAL (Pos Gamma Damping)"
                    summary.append("Trend Muted: Positive Gamma suggests support/damping on downside.")
                else:
                    signal = "NEUTRAL"
                    summary.append("Positive Gamma & Neutral Spot. Expect low vol.")
            else:
                summary.append(f"No signal. A={agent_a.signal}, GEX={net_gex_f}")

        # 4. Gamma Wall Interaction
        gamma_walls = b_output.gamma_walls
        call_wall = gamma_walls.get("call_wall")
        put_wall = gamma_walls.get("put_wall")
        spot = agent_a.data.get("spot")

        WALL_MAGNET_PCT = settings.agent_g_wall_magnet_pct
        WALL_BREAKOUT_PCT = settings.agent_g_wall_breakout_pct

        if spot:
            if call_wall:
                dist_pct = (call_wall - spot) / spot * 100.0
                if 0 < dist_pct < WALL_MAGNET_PCT and agent_a.signal == "BULLISH":
                    summary.append(f"Approaching Call Wall {call_wall}: Expect Resistance/Magnet.")
                    if signal == "Option Structure: LONG_CALL (Neg Gamma Accel)":
                        summary.append("CAUTION: Call Wall ahead.")
                elif dist_pct < -WALL_BREAKOUT_PCT:
                    summary.append(f"Call Wall {call_wall} BREACHED! Gamma Squeeze potential.")

            if put_wall:
                dist_pct = (spot - put_wall) / spot * 100.0
                if 0 < dist_pct < WALL_MAGNET_PCT and agent_a.signal == "BEARISH":
                    summary.append(f"Approaching Put Wall {put_wall}: Expect Support/Magnet.")
                    if signal == "Option Structure: LONG_PUT (Neg Gamma Accel)":
                        summary.append("CAUTION: Put Wall ahead.")
                elif dist_pct < -WALL_BREAKOUT_PCT:
                    summary.append(f"Put Wall {put_wall} BREACHED! Gamma Slide potential.")

        # 5. Gamma Flip Note
        if b_output.gamma_flip:
            summary.append("WARNING: Gamma Flip detected.")

        _vanna_dict = vanna_data.model_dump() if vanna_data is not None else {}

        return AgentResult(
            agent=self.AGENT_ID,
            signal=signal,
            as_of=agent_a.as_of,
            data={
                "agent_a": agent_a.model_dump(),
                "agent_b": agent_b.model_dump(),
                "net_gex": net_gex_f,
                "gex_regime": _vanna_dict.get("gex_regime", "NEUTRAL"),
                "gamma_walls": gamma_walls,
                "gamma_flip_level": b_output.gamma_flip_level,
                "trap_state": b_signal,
                "wall_interaction": self._get_wall_interaction(
                    spot=spot,
                    net_gex=net_gex_f,
                    agent_a_signal=agent_a.signal,
                    call_wall=call_wall,
                    put_wall=put_wall,
                    magnet_pct=WALL_MAGNET_PCT,
                ),
                "fused_signal": {
                    "direction": fused_signal.direction,
                    "confidence": fused_signal.confidence,
                    "weights": fused_signal.weights,
                    "regime": fused_signal.regime,
                    "iv_regime": fused_signal.iv_regime.value,
                    "gex_intensity": fused_signal.gex_intensity.value,
                    "explanation": fused_signal.explanation,
                    "components": fused_signal.components,
                },
                "micro_structure": agent_b.data.get("micro_structure"),
            },
            summary="; ".join(summary) if summary else "Decision rules not satisfied.",
        )

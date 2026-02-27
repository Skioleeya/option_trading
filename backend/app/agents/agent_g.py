from __future__ import annotations

import logging
from typing import Any

from app.agents.agent_a import AgentA
from app.agents.agent_b import AgentB1, DivergenceState
from app.agents.base import AgentResult
from app.config import settings
from app.models.agent_output import AgentB1Output
from app.services.fusion.dynamic_weight_engine import DynamicWeightEngine
from app.ui.micro_stats.presenter import MicroStatsPresenter
from app.ui.tactical_triad.presenter import TacticalTriadPresenter
from app.ui.skew_dynamics.presenter import SkewDynamicsPresenter
from app.ui.active_options.presenter import ActiveOptionsPresenter
from app.ui.mtf_flow.presenter import MTFFlowPresenter


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
        self._active_options_presenter = ActiveOptionsPresenter()

    async def set_redis_client(self, client: Any) -> None:
        """Inject shared Redis client into sub-agents and self (for DEG-FLOW)."""
        self._redis = client
        await self._agent_b.set_redis_client(client)

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

    async def run(self, snapshot: dict[str, Any]) -> AgentResult:
        # 1. Run B1 first to get dynamic thresholds from Vanna
        b = self._agent_b.run(snapshot)
        
        # 2. Extract momentum multiplier for A
        vanna_res = b.data.get("micro_structure", {}).get("micro_structure_state", {}).get("vanna_flow_result", {})
        mom_mult = vanna_res.get("momentum_slope_multiplier", 1.0) if vanna_res else 1.0
        
        # 3. Run A with dynamic scaling
        a = self._agent_a.run(snapshot, slope_multiplier=mom_mult)
        
        return await self.decide(agent_a=a, agent_b=b, snapshot=snapshot)

    async def decide(self, *, agent_a: AgentResult, agent_b: AgentResult, snapshot: dict[str, Any]) -> AgentResult:
        """Top-level guard wrapper."""
        try:
            return await self._decide_impl(agent_a=agent_a, agent_b=agent_b, snapshot=snapshot)
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

    async def _decide_impl(self, *, agent_a: AgentResult, agent_b: AgentResult, snapshot: dict[str, Any]) -> AgentResult:
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

        vib_data = ms_state.volume_imbalance if ms_state else None
        jump_data = ms_state.jump_detection if ms_state else None

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
        
        # Phase 27.4 — Vanna Direction Correction (Paper 4 & 5)
        # Danger zone in highly compressed timeframes (<30m) often results in Bullish chasing
        if vanna_data and vanna_data.state == "DANGER_ZONE":
            # For now, we assume high-frequency mode is always active. 
            # In production, this would check `time_since_state_entered`.
            vanna_direction = "BULLISH" # Chase the jump
            summary.append("VANNA CORRECT: Danger Zone mapped to BULLISH chasing (Paper 5).")

        mtf_direction = mtf_consensus.get("consensus", "NEUTRAL")
        vib_direction = vib_data.consensus if vib_data else "NEUTRAL"

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
            vib_signal={
                "direction": vib_direction,
                "confidence": vib_data.strength if vib_data else 0.0,
            },
        )

        # 1.5. Phase 27.3 — Jump Gate Safety Valve (P0.1, highest priority lockout)
        # Paper 5: Aura et al. — Jumps indicate delta-hedging failure. 
        # Halt execution until mean-reversion or stabilization.
        if jump_data and jump_data.is_jump:
            signal = f"HOLD (JUMP_DETECTED: |Z|={abs(jump_data.z_score):.1f})"
            summary.append(
                f"SAFETY VALVE (P0.1): Price shock detected ({jump_data.magnitude_pct:+.2f}%). "
                "Halting trade entry per Paper 5 safety protocol."
            )
            # Early return or set flag to skip ALL downstream
            return AgentResult(
                agent=self.AGENT_ID,
                signal=signal,
                as_of=agent_b.as_of,
                data={**agent_b.data, "fused_signal": fused_signal.model_dump()},
                summary="; ".join(summary)
            )

        # Phase 25A — VRP Veto Gate (P0.5, fires before trap detection)
        # Paper: Muravyev et al. (SSRN #4019647) — "EV < 0 when options are too expensive"
        vrp_value = agent_b.data.get("hv_analysis", {}).get("vrp", None)
        vrp_state  = agent_b.data.get("hv_analysis", {}).get("premium_state", "FAIR")

        vrp_vetoed = False
        if vrp_value is not None and vrp_value > settings.vrp_veto_threshold:
            signal = f"NO_TRADE (VRP_VETO: VRP={vrp_value:.1f}≫{settings.vrp_veto_threshold})"
            summary.append(
                f"VRP VETO (P0.5): IV={spy_atm_iv:.1f}% far too expensive (VRP={vrp_value:.1f}). "
                "Entry EV<0 per Muravyev et al. (SSRN #4019647)."
            )
            vrp_vetoed = True

        # Phase 25B — MTF Alignment confidence dampener (Paper 1)
        # Paper: Dim et al. (SSRN #4692190) — MTF alignment < 0.34 → confidence cut 50%
        mtf_alignment = mtf_consensus.get("alignment", 1.0)
        if mtf_alignment < 0.34:
            fused_signal_confidence = fused_signal.confidence * 0.5
            summary.append(f"MTF ALIGN DAMP: alignment={mtf_alignment:.2f} → conf halved.")
        elif mtf_alignment >= 0.67 and vrp_state == "BARGAIN":
            # VRP Bargain + MTF fully aligned = best entry condition
            fused_signal_confidence = min(fused_signal.confidence * settings.vrp_bargain_boost, 1.0)
            summary.append(f"VRP BARGAIN BOOST: alignment={mtf_alignment:.2f}, VRP={vrp_value:.1f}")
        else:
            fused_signal_confidence = fused_signal.confidence

        # Phase 25D — GEX Directional Refinement (Paper 4)
        # GEX < -500M indicates momentum acceleration risk. 
        # Signals aligning with the gamma-induced move should get higher confidence.
        gex_accel_boost = 1.0
        if net_gex_f < -500:
            if fused_signal.direction == "BEARISH":
                gex_accel_boost = 1.20 # Reinforce crash
                summary.append("GEX ACCEL: Neg Gamma reinforcing Bearish move (Paper 4).")
            elif fused_signal.direction == "BULLISH":
                gex_accel_boost = 1.15 # Reinforce short squeeze
                summary.append("GEX ACCEL: Neg Gamma reinforcing Bullish bounce (Short Squeeze).")
        elif net_gex_f > 800 and fused_signal.direction == "NEUTRAL":
            summary.append("GEX PINNING: Strong Pos Gamma limiting volatility (Paper 2).")

        fused_signal_confidence = min(fused_signal_confidence * gex_accel_boost, 1.0)

        if net_gex_f < -1000:
            summary.append("⚠️ TAIL RISK: Extreme Negative GEX detected (-1000M+).")

        # Patch adjusted confidence back so downstream reads it
        object.__setattr__(fused_signal, 'confidence', fused_signal_confidence)

        # 2. Trap Logic (Priority 1) — only if not VRP vetoed
        if vrp_vetoed:
            pass  # signal already set above; skip all decision layers
        elif b_signal == DivergenceState.ACTIVE_BULL_TRAP:
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
        micro_state = agent_b.data.get("micro_structure", {}).get("micro_structure_state", {})

        # Extract Greeks for Tactical Triad
        # In a real scenario these come from Agent B's option scan / IV surfaces
        # We dummy-fallback to 0.0 if not fully integrated in `AgentB1Output` yet
        vrp = vrp_value  # use real VRP from hv_analysis (not gamma_flip_level placeholder)
        net_charm = None  # Add to b1 schema later if needed

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
                "ui_state": {
                    "micro_stats": MicroStatsPresenter.build(
                        gex_regime=_vanna_dict.get("gex_regime", "NEUTRAL"),
                        wall_dyn=wall_data.model_dump() if wall_data else {},
                        vanna=vanna_data.state if vanna_data else "NORMAL",
                        momentum=agent_a.signal,
                    ),
                    "tactical_triad": TacticalTriadPresenter.build(
                        vrp=agent_b.data.get("hv_analysis", {}).get("vrp"),
                        vrp_state=agent_b.data.get("hv_analysis", {}).get("premium_state"),
                        net_charm=agent_b.data.get("charm_analysis", {}).get("net_charm"),
                        svol_corr=vanna_data.correlation if vanna_data else None,
                        svol_state=vanna_data.state if vanna_data else "NORMAL",
                        fused_signal_direction=fused_signal.direction
                    ),
                    "skew_dynamics": SkewDynamicsPresenter.build(
                        skew_val=agent_b.data.get("skew_analysis", {}).get("skew_value", 0.0),
                        state=agent_b.data.get("skew_analysis", {}).get("skew_state", "NEUTRAL")
                    ),
                    "active_options": await self._active_options_presenter.build(
                        chain=snapshot.get("chain", []),
                        spot=snapshot.get("spot") or 0.0,
                        atm_iv=agent_b.data.get("spy_atm_iv") or 0.0,
                        gex_regime=_vanna_dict.get("gex_regime", "NEUTRAL"),
                        redis=getattr(self, "_redis", None),
                        limit=5
                    ),
                    "mtf_flow": MTFFlowPresenter.build(
                        mtf_consensus=mtf_consensus
                    )
                },
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

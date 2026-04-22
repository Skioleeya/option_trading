from __future__ import annotations
import logging
from typing import Any
from l2_decision.agents.agent_a import AgentA
from l2_decision.agents.agent_b import AgentB1, DivergenceState
from l2_decision.agents.base import AgentResult
from l2_decision.agents.services.agent_g_decision_support import (
    MAX_SIGNAL_CONFIDENCE,
    VOL_ACCEL_SQUEEZE_CONFIDENCE_BOOST,
    VRP_VETO_EXIT_RATIO,
    build_micro_flow_signal,
    collect_atm_micro_metrics,
    extract_dealer_squeeze_alert,
    extract_per_strike,
    safe_get_value,
)
from l2_decision.agents.services.agent_g_policy_support import (
    append_sync_gap_diagnostic,
    apply_mtf_alignment_policy,
    apply_vrp_veto,
    build_jump_gate_result,
    clamp01,
    derive_mtf_geometry,
    gex_accel_boost,
    map_iv_to_direction,
    map_vanna_to_direction,
    map_wall_to_direction,
    resolve_signal,
    resolve_idle_trend_signal,
    resolve_vrp,
)
from l2_decision.signals.fusion.dynamic_weight_engine import DynamicWeightEngine
from shared.config import settings
from shared_rust.models import AgentB1Output
from shared_rust.services import (
    tactical_classify_vrp_state as classify_vrp_state,
    tactical_compute_vrp as compute_vrp,
)
logger = logging.getLogger(__name__)
class AgentG:
    AGENT_ID = "agent_g"
    def __init__(self, agent_a: AgentA | None = None, agent_b: AgentB1 | None = None):
        self._agent_a = agent_a or AgentA()
        self._agent_b = agent_b or AgentB1()
        self._weight_engine = DynamicWeightEngine()
        # Hysteresis States (Fixing Boundary Flicker)
        self._vrp_active = False
        self._mtf_damped = False
        # PP-L3C FIX: Persist last valid UI state to bridge transient calculation gaps
        self._last_ui_state: dict[str, Any] = {}

    async def set_redis_client(self, client: Any) -> None:
        """Inject shared Redis client into sub-agents and self (for DEG-FLOW)."""
        self._redis = client
        await self._agent_b.set_redis_client(client)

    async def run(self, snapshot: dict[str, Any] | Any) -> AgentResult:
        # PP-L2 Robust: snapshot can be EnrichedSnapshot or legacy dict
        b = self._agent_b.run(snapshot)

        # 2. Extract momentum multiplier for A
        m_state = (b.data.get("micro_structure") or {}).get("micro_structure_state") or {}
        vanna_res = m_state.get("vanna_flow_result") or m_state.get("vanna_flow", {}) if isinstance(m_state, dict) else {}
        mom_mult = vanna_res.get("momentum_slope_multiplier", 1.0) if vanna_res else 1.0

        a = self._agent_a.run(snapshot, slope_multiplier=mom_mult)
        return await self.decide(agent_a=a, agent_b=b, snapshot=snapshot)

    async def decide(self, *, agent_a: AgentResult, agent_b: AgentResult, snapshot: dict[str, Any]) -> AgentResult:
        """Top-level guard wrapper."""
        try:
            res = await self._decide_impl(agent_a=agent_a, agent_b=agent_b, snapshot=snapshot)
            if res.data and "ui_state" in res.data:
                self._last_ui_state = res.data["ui_state"]
            return res
        except Exception as exc:
            logger.exception("[AgentG] decide() crashed; emitting NO_TRADE safety fallback: %s", exc)
            data = {
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
            }
            if self._last_ui_state:
                data["ui_state"] = self._last_ui_state

            return AgentResult(
                agent=self.AGENT_ID,
                signal="NO_TRADE",
                as_of=agent_a.as_of,
                data=data,
                summary="AgentG.decide() exception; NO_TRADE issued.",
            )

    async def _decide_impl(self, *, agent_a: AgentResult, agent_b: AgentResult, snapshot: dict[str, Any]) -> AgentResult:
        b_output = AgentB1Output.model_validate(agent_b.data)
        summary: list[str] = []
        signal = "NO_TRADE"

        net_gex_f = b_output.net_gex
        spy_atm_iv = b_output.spy_atm_iv
        b_signal = agent_b.signal

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

        self._append_sync_gap_diagnostic(summary, agent_b.data)
        self._weight_engine.update_market_state(spy_atm_iv, net_gex_f)

        iv_confidence = b_output.iv_confidence or (iv_data.confidence if iv_data else 0.0)
        wall_confidence = b_output.wall_confidence or (wall_data.confidence if wall_data else 0.0)
        vanna_confidence = b_output.vanna_confidence or (vanna_data.confidence if vanna_data else 0.0)

        iv_direction = map_iv_to_direction(iv_data.state if iv_data else None)
        wall_direction = map_wall_to_direction(
            wall_data.call_wall_state if wall_data else None,
            wall_data.put_wall_state if wall_data else None,
        )
        vanna_direction = map_vanna_to_direction(vanna_data.state if vanna_data else None)

        mtf_state, mtf_confidence, raw_mtf_alignment = derive_mtf_geometry(mtf_consensus, clamp01)
        mtf_direction = "BULLISH" if mtf_state > 0 else ("BEARISH" if mtf_state < 0 else "NEUTRAL")
        vib_direction = vib_data.consensus if vib_data else "NEUTRAL"

        vrp, premium_state = self._resolve_vrp(spy_atm_iv=spy_atm_iv, hv_analysis=b_output.hv_analysis or {})

        spot_price = float(agent_a.data.get("spot") or 0.0)
        per_strike = extract_per_strike(snapshot)
        avg_tox, avg_bbo, avg_atm_vpin = collect_atm_micro_metrics(per_strike=per_strike, spot=spot_price)
        fallback_bbo = float(safe_get_value(snapshot, "bbo_imbalance", 0.0) or 0.0)
        micro_flow_signal_dict, avg_bbo = build_micro_flow_signal(
            avg_tox=avg_tox,
            avg_bbo=avg_bbo,
            fallback_bbo=fallback_bbo,
            net_gex=net_gex_f,
            threshold=settings.micro_flow_toxicity_threshold,
        )
        if avg_atm_vpin == 0.0:
            avg_atm_vpin = float(safe_get_value(snapshot, "vpin_score", 0.0) or 0.0)
        micro_flow_signal_dict["avg_atm_vpin_score"] = avg_atm_vpin

        if avg_tox != 0.0 or avg_bbo != 0.0:
            logger.debug(
                "[AgentG.Phase3] micro_flow: tox=%.3f bbo=%.3f -> %s (conf=%.2f)",
                avg_tox,
                avg_bbo,
                micro_flow_signal_dict["direction"],
                micro_flow_signal_dict["confidence"],
            )

        fused_signal = self._weight_engine.calculate_weights(
            iv_signal={"direction": iv_direction, "confidence": iv_confidence},
            wall_signal={"direction": wall_direction, "confidence": wall_confidence},
            vanna_signal={"direction": vanna_direction, "confidence": vanna_confidence},
            mtf_signal={"direction": mtf_direction, "confidence": mtf_confidence},
            vib_signal={"direction": vib_direction, "confidence": vib_data.strength if vib_data else 0.0},
            micro_flow_signal=micro_flow_signal_dict,
        )

        jump_result = self._build_jump_gate_result(jump_data=jump_data, agent_b=agent_b, fused_signal=fused_signal, summary=summary)
        if jump_result is not None:
            return jump_result

        vrp_vetoed = False
        if vrp is not None:
            vrp_vetoed, signal = self._apply_vrp_veto(signal=signal, summary=summary, vrp=vrp, spy_atm_iv=spy_atm_iv)
        else:
            logger.debug("[AgentG] VRP veto skipped: vrp=None (vrp_baseline_hv not configured or HV unavailable)")

        dealer_squeeze_alert = extract_dealer_squeeze_alert(ms_state, agent_b.data)
        adjusted_confidence = self._compute_adjusted_confidence(
            summary=summary,
            fused_signal=fused_signal,
            mtf_alignment=raw_mtf_alignment,
            premium_state=premium_state,
            vrp=vrp,
            net_gex=net_gex_f,
            dealer_squeeze_alert=dealer_squeeze_alert,
            avg_atm_vpin=avg_atm_vpin,
        )
        fused_signal.confidence = adjusted_confidence

        if not vrp_vetoed:
            signal = self._resolve_signal(
                current_signal=signal,
                summary=summary,
                b_signal=b_signal,
                fused_signal=fused_signal,
                net_gex=net_gex_f,
                agent_a_signal=agent_a.signal,
            )

        if b_output.gamma_flip:
            summary.append("WARNING: Gamma Flip detected.")

        result = AgentResult(
            agent=self.AGENT_ID,
            signal=signal,
            as_of=agent_a.as_of,
            data={
                "fused_signal": {
                    "direction": fused_signal.direction,
                    "confidence": fused_signal.confidence,
                    "weights": fused_signal.weights,
                    "regime": fused_signal.regime,
                    "iv_regime": str(fused_signal.iv_regime),
                    "gex_intensity": str(fused_signal.gex_intensity),
                    "explanation": fused_signal.explanation,
                    "components": fused_signal.components,
                    "raw_vpin": avg_atm_vpin,
                    "raw_bbo_imb": avg_bbo,
                    "raw_vol_accel": vib_data.vol_accel_ratio if vib_data else 0.0,
                },
                "micro_structure": agent_b.data.get("micro_structure"),
            },
            summary="; ".join(summary) if summary else "Decision rules not satisfied.",
        )
        logger.info("[L2 AgentG] Final Signal: %s | Gate Winner Statement: %s", result.signal, result.summary)
        return result

    def _append_sync_gap_diagnostic(self, summary: list[str], agent_b_data: dict[str, Any]) -> None:
        append_sync_gap_diagnostic(summary, agent_b_data, settings.agent_b_gamma_tick_interval, logger)

    def _resolve_vrp(self, *, spy_atm_iv: float | None, hv_analysis: dict[str, Any]) -> tuple[float | None, str]:
        return resolve_vrp(
            spy_atm_iv=spy_atm_iv,
            hv_analysis=hv_analysis,
            vrp_baseline_hv=settings.vrp_baseline_hv,
            vrp_cheap_threshold=settings.vrp_cheap_threshold,
            vrp_expensive_threshold=settings.vrp_expensive_threshold,
            vrp_trap_threshold=settings.vrp_trap_threshold,
            compute_vrp=compute_vrp,
            classify_vrp_state=classify_vrp_state,
        )

    def _build_jump_gate_result(
        self,
        *,
        jump_data: Any,
        agent_b: AgentResult,
        fused_signal: Any,
        summary: list[str],
    ) -> AgentResult | None:
        return build_jump_gate_result(
            agent_id=self.AGENT_ID,
            jump_data=jump_data,
            agent_b=agent_b,
            fused_signal=fused_signal,
            summary=summary,
        )

    def _apply_vrp_veto(
        self,
        *,
        signal: str,
        summary: list[str],
        vrp: float,
        spy_atm_iv: float | None,
    ) -> tuple[bool, str]:
        self._vrp_active, vetoed, next_signal = apply_vrp_veto(
            vrp_active=self._vrp_active,
            signal=signal,
            summary=summary,
            vrp=vrp,
            spy_atm_iv=spy_atm_iv,
            entry_threshold=settings.vrp_veto_threshold,
            exit_ratio=VRP_VETO_EXIT_RATIO,
            logger=logger,
        )
        return vetoed, next_signal

    def _compute_adjusted_confidence(
        self,
        *,
        summary: list[str],
        fused_signal: Any,
        mtf_alignment: float,
        premium_state: str,
        vrp: float | None,
        net_gex: float | None,
        dealer_squeeze_alert: bool,
        avg_atm_vpin: float,
    ) -> float:
        confidence = self._apply_mtf_alignment_policy(
            summary=summary,
            fused_signal=fused_signal,
            mtf_alignment=mtf_alignment,
            premium_state=premium_state,
            vrp=vrp,
        )
        gex_accel_boost = self._gex_accel_boost(
            summary=summary,
            fused_signal=fused_signal,
            net_gex=net_gex,
        )
        confidence = min(confidence * gex_accel_boost, MAX_SIGNAL_CONFIDENCE)
        if not dealer_squeeze_alert:
            return confidence
        confidence = min(confidence * VOL_ACCEL_SQUEEZE_CONFIDENCE_BOOST, MAX_SIGNAL_CONFIDENCE)
        summary.append("VOL ACCEL SQUEEZE: High volume burst in Neg Gamma -> Risk elevated.")
        logger.info(
            "[AgentG.Practice3] VOL ACCEL SQUEEZE: avg_vpin=%.3f dir=%s confx%.2f",
            avg_atm_vpin,
            fused_signal.direction,
            VOL_ACCEL_SQUEEZE_CONFIDENCE_BOOST,
        )
        return confidence

    def _apply_mtf_alignment_policy(
        self,
        *,
        summary: list[str],
        fused_signal: Any,
        mtf_alignment: float,
        premium_state: str,
        vrp: float | None,
    ) -> float:
        self._mtf_damped, confidence = apply_mtf_alignment_policy(
            mtf_damped=self._mtf_damped,
            summary=summary,
            fused_signal=fused_signal,
            mtf_alignment=mtf_alignment,
            premium_state=premium_state,
            vrp=vrp,
            mtf_entry_threshold=settings.mtf_alignment_damp_entry,
            mtf_exit_threshold=settings.mtf_alignment_damp_exit,
            vrp_bargain_boost=settings.vrp_bargain_boost,
            max_signal_confidence=MAX_SIGNAL_CONFIDENCE,
            logger=logger,
        )
        return confidence

    def _gex_accel_boost(
        self,
        *,
        summary: list[str],
        fused_signal: Any,
        net_gex: float | None,
    ) -> float:
        return gex_accel_boost(
            summary=summary,
            fused_signal=fused_signal,
            net_gex=net_gex,
            gex_accel_threshold=settings.gex_accel_threshold,
            gex_accel_boost_bearish=settings.gex_accel_boost_bearish,
            gex_accel_boost_bullish=settings.gex_accel_boost_bullish,
        )

    def _resolve_signal(
        self,
        *,
        current_signal: str,
        summary: list[str],
        b_signal: str,
        fused_signal: Any,
        net_gex: float | None,
        agent_a_signal: str,
    ) -> str:
        return resolve_signal(
            current_signal=current_signal,
            summary=summary,
            b_signal=b_signal,
            fused_signal=fused_signal,
            net_gex=net_gex,
            agent_a_signal=agent_a_signal,
            active_bull_trap=DivergenceState.ACTIVE_BULL_TRAP,
            active_bear_trap=DivergenceState.ACTIVE_BEAR_TRAP,
            idle_state=DivergenceState.IDLE,
            fusion_confidence_threshold=settings.fusion_confidence_threshold,
        )

    def _resolve_idle_trend_signal(
        self,
        *,
        summary: list[str],
        net_gex: float | None,
        agent_a_signal: str,
        current_signal: str,
    ) -> str:
        return resolve_idle_trend_signal(
            summary=summary,
            net_gex=net_gex,
            agent_a_signal=agent_a_signal,
            current_signal=current_signal,
        )

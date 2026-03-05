from __future__ import annotations

import logging
from typing import Any

from l2_decision.agents.agent_a import AgentA
from l2_decision.agents.agent_b import AgentB1, DivergenceState
from l2_decision.agents.base import AgentResult
from shared.config import settings
from shared.models.agent_output import AgentB1Output
from l2_decision.signals.fusion.dynamic_weight_engine import DynamicWeightEngine
from l3_assembly.presenters.ui.active_options.presenter import ActiveOptionsPresenter


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

        # Hysteresis States (Fixing Boundary Flicker)
        self._vrp_active = False    # True if currently in VRP Veto state
        self._mtf_damped = False    # True if currently in MTF Alignment Damping state

        # PP-2 FIX: EWMA smoothed MTF alignment to eliminate single-tick discrete jumps
        self._mtf_alignment_ema: float | None = None
        
        # PP-L3C FIX: Persist last valid UI state to bridge transient calculation gaps
        self._last_ui_state: dict[str, Any] = {}

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
        """Map vanna flow state to direction.

        DANGER_ZONE: Positive Spot-IV correlation in compressed timeframes
        signals dealer delta-hedging unwinding → short-squeeze fuel.
        Both academic papers (4 & 5) and the original override logic agree
        this maps to BULLISH. Unifying here so there is exactly ONE place
        that defines this mapping — no secondary override needed.

        PP-3 FIX: GRIND_STABLE was incorrectly mapped to BULLISH (causing
        NORMAL→GRIND_STABLE transitions to inject a spurious BULLISH vanna
        signal). Corrected to NEUTRAL — stable grinding is not directional.
        """
        if vanna_state == "DANGER_ZONE":
            return "BULLISH"   # FIX C/F: was BEARISH in map, then overridden BULLISH elsewhere
        elif vanna_state == "GRIND_STABLE":
            return "NEUTRAL"   # PP-3 FIX: was BULLISH, now NEUTRAL (no spurious direction)
        else:
            return "NEUTRAL"

    async def run(self, snapshot: dict[str, Any] | Any) -> AgentResult:
        # PP-L2 Robust: snapshot can be EnrichedSnapshot or legacy dict
        # 1. Run B1 first to get dynamic thresholds from Vanna
        b = self._agent_b.run(snapshot)
        
        # 2. Extract momentum multiplier for A
        # Use safe extraction
        def _get_val(obj, key, default=None):
            if hasattr(obj, key): return getattr(obj, key, default)
            if isinstance(obj, dict): return obj.get(key, default)
            return default
            
        m_state = (b.data.get("micro_structure") or {}).get("micro_structure_state") or {}
        vanna_res = m_state.get("vanna_flow_result") or m_state.get("vanna_flow", {}) if isinstance(m_state, dict) else {}
        mom_mult = vanna_res.get("momentum_slope_multiplier", 1.0) if vanna_res else 1.0
        
        # 3. Run A with dynamic scaling
        a = self._agent_a.run(snapshot, slope_multiplier=mom_mult)
        
        return await self.decide(agent_a=a, agent_b=b, snapshot=snapshot)

    async def decide(self, *, agent_a: AgentResult, agent_b: AgentResult, snapshot: dict[str, Any]) -> AgentResult:
        """Top-level guard wrapper."""
        try:
            res = await self._decide_impl(agent_a=agent_a, agent_b=agent_b, snapshot=snapshot)
            # PP-L3C: Record the ui_state if present
            if res.data and "ui_state" in res.data:
                self._last_ui_state = res.data["ui_state"]
            return res
        except Exception:
            logger.exception("[AgentG] decide() crashed; emitting NO_TRADE safety fallback")
            
            # PP-L3C: Fallback still tries to provide UI state
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

        # PP-5 FIX: Dual-rate sync staleness detection.
        # trap_micro_sync_gap > 0 means trap state is older than the current micro snapshot.
        # This is expected and normal (throttle design), but if the gap grows beyond
        # reasonable bounds, log a diagnostic so operators can tune gamma_tick_interval.
        # IMPORTANT: Jump detection and Vanna multipliers are ALWAYS fresh (updated every tick)
        # regardless of trap staleness, so no signal dampening is applied here.
        sync_gap = agent_b.data.get("trap_micro_sync_gap", 0.0) or 0.0
        if sync_gap > settings.agent_b_gamma_tick_interval * 3:
            summary.append(
                f"[PP-5 DIAG] Trap state stale: trap_micro_sync_gap={sync_gap:.2f}s "
                f"(>{settings.agent_b_gamma_tick_interval * 3:.1f}s). "
                "Consider reducing agent_b_gamma_tick_interval."
            )
            logger.debug("[AgentG] PP-5: trap/micro sync gap=%.2fs", sync_gap)

        # Map microstructure states to directions
        iv_direction = self._map_iv_to_direction(iv_data.state if iv_data else None)
        wall_direction = self._map_wall_to_direction(
            wall_data.call_wall_state if wall_data else None,
            wall_data.put_wall_state if wall_data else None,
        )
        vanna_direction = self._map_vanna_to_direction(vanna_data.state if vanna_data else None)
        
        mtf_direction = mtf_consensus.get("consensus", "NEUTRAL")
        vib_direction = vib_data.consensus if vib_data else "NEUTRAL"

        # Update weight engine
        self._weight_engine.update_market_state(spy_atm_iv, net_gex_f)

        # Tactical Triad Metrics Computation (Refactor: Sourced from AgentB)
        b_hv = b_output.hv_analysis or {}
        vrp = b_hv.get("vrp")
        premium_state = b_hv.get("premium_state", "FAIR")

        # Fallback for direct calculation (Fix: decimal * 100 for PCT conversion)
        if vrp is None and spy_atm_iv is not None:
             baseline_hv = settings.vrp_baseline_hv
             vrp = (spy_atm_iv * 100.0 - baseline_hv)
        
        premium_state = "FAIR"
        if vrp is not None:
            if vrp > settings.vrp_trap_threshold:
                premium_state = "TRAP"
            elif vrp > settings.vrp_expensive_threshold:
                premium_state = "EXPENSIVE"
            elif vrp < (settings.vrp_cheap_threshold * 3):
                premium_state = "BARGAIN"
            elif vrp < settings.vrp_cheap_threshold:
                premium_state = "CHEAP"

        # Helper for L1 Object/Dict parity
        def _get_val(obj, key, default=None):
            if hasattr(obj, key): return getattr(obj, key, default)
            if isinstance(obj, dict): return obj.get(key, default)
            return default

        per_strike = _get_val(snapshot, "per_strike_gex") or []
        _spot = agent_a.data.get("spot") or 0.0

        # Optimization: Use pyarrow pylist if snapshot is EnrichedSnapshot and chain is Pa Batch
        if hasattr(snapshot, "chain"):
             try:
                 import pyarrow as pa
                 if isinstance(snapshot.chain, pa.RecordBatch):
                     per_strike = snapshot.chain.to_pylist()
             except: pass

        atm_tox_vals: list[float] = []
        atm_bbo_vals: list[float] = []
        for row in per_strike:
            row_strike = row.get("strike", 0) if isinstance(row, dict) else getattr(row, "strike", 0)
            if abs(row_strike - _spot) <= 3.0:   # ATM ±3 strike window (Paper 1: ATM OFI 更稳定)
                tox = row.get("toxicity_score", 0.0) if isinstance(row, dict) else getattr(row, "toxicity_score", 0.0)
                bbo = row.get("bbo_imbalance", 0.0) if isinstance(row, dict) else getattr(row, "bbo_imbalance", 0.0)
                if tox != 0.0:
                    atm_tox_vals.append(float(tox))
                if bbo != 0.0:
                    atm_bbo_vals.append(float(bbo))

        avg_tox = sum(atm_tox_vals) / len(atm_tox_vals) if atm_tox_vals else 0.0
        avg_bbo = sum(atm_bbo_vals) / len(atm_bbo_vals) if atm_bbo_vals else 0.0
        if avg_bbo == 0.0:
            avg_bbo = _get_val(snapshot, "bbo_imbalance", 0.0)

        # Paper 3: GEX-adaptive blend — neg GEX favors BBO (MM hedging signal quality rises)
        _bbo_w = 0.60 if (net_gex_f is not None and net_gex_f < 0) else 0.40
        _tox_w = 1.0 - _bbo_w
        micro_score = _tox_w * avg_tox + _bbo_w * avg_bbo

        _mf_th = settings.micro_flow_toxicity_threshold  # default 0.25
        if micro_score > _mf_th:
            micro_flow_direction = "BULLISH"
            micro_flow_confidence = min(abs(micro_score), 1.0)
        elif micro_score < -_mf_th:
            micro_flow_direction = "BEARISH"
            micro_flow_confidence = min(abs(micro_score), 1.0)
        else:
            micro_flow_direction = "NEUTRAL"
            micro_flow_confidence = 0.0

        micro_flow_signal_dict = {
            "direction": micro_flow_direction,
            "confidence": micro_flow_confidence,
        }

        if avg_tox != 0.0 or avg_bbo != 0.0:
            logger.debug(
                "[AgentG.Phase3] micro_flow: tox=%.3f bbo=%.3f score=%.3f → %s (conf=%.2f)",
                avg_tox, avg_bbo, micro_score, micro_flow_direction, micro_flow_confidence,
            )
        # ── Practice 2: ATM VPIN Score Aggregation (diagnostic field) ───────
        # Aggregate vpin_score from per-strike flow snapshot for ATM strikes (±3 window).
        atm_vpin_vals: list[float] = []
        for row in per_strike:
            row_strike = row.get("strike", 0) if isinstance(row, dict) else getattr(row, "strike", 0)
            if abs(row_strike - _spot) <= 3.0:
                vpin_s = row.get("vpin_score", None) if isinstance(row, dict) else getattr(row, "vpin_score", None)
                if vpin_s is not None and vpin_s != 0.0:
                    atm_vpin_vals.append(float(vpin_s))

        avg_atm_vpin = sum(atm_vpin_vals) / len(atm_vpin_vals) if atm_vpin_vals else 0.0
        if avg_atm_vpin == 0.0:
            avg_atm_vpin = snapshot.get("vpin_score", 0.0)
        micro_flow_signal_dict["avg_atm_vpin_score"] = avg_atm_vpin

        # ── Practice 3: dealer_squeeze_alert from micro state ────────────────
        # Read flag set by AgentB1._run_microstructure (vol_accel ≥ threshold AND net_gex < 0).
        # Primary path: typed MicroStructureState.dealer_squeeze_alert
        # Fallback path: raw dict from agent_b.data (throttled-cache path)
        dealer_squeeze_alert: bool = False
        if ms_state is not None:
            dealer_squeeze_alert = getattr(ms_state, "dealer_squeeze_alert", False)
        if not dealer_squeeze_alert:
            raw_micro_state = agent_b.data.get("micro_structure", {}).get("micro_structure_state", {})
            if isinstance(raw_micro_state, dict):
                dealer_squeeze_alert = bool(raw_micro_state.get("dealer_squeeze_alert", False))

        # ── Calculate fused signal ──────────────────────────────────────────


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
            micro_flow_signal=micro_flow_signal_dict,
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

        vrp_vetoed = False
        if vrp is not None:
            # Hysteresis: Entry > threshold, Exit < threshold * 0.95
            entry_th = settings.vrp_veto_threshold
            exit_th = entry_th * 0.95
            
            if not self._vrp_active and vrp > entry_th:
                self._vrp_active = True
                logger.warning(f"[AgentG] VRP Veto ACTIVATED: {vrp:.1f} > {entry_th}")
            elif self._vrp_active and vrp < exit_th:
                self._vrp_active = False
                logger.warning(f"[AgentG] VRP Veto DEACTIVATED: {vrp:.1f} < {exit_th}")

            if self._vrp_active:
                signal = f"NO_TRADE (VRP_VETO: VRP={vrp:.1f})"
                summary.append(
                    f"VRP VETO (P0.5): IV={spy_atm_iv:.1f}% far too expensive (VRP={vrp:.1f}). "
                    "Entry EV<0 per Muravyev et al. (SSRN #4019647)."
                )
                vrp_vetoed = True

        # Phase 25B — MTF Alignment confidence dampener (Paper 1)
        # Paper: Dim et al. (SSRN #4692190) — MTF alignment < 0.34 → confidence cut 50%
        raw_mtf_alignment = mtf_consensus.get("alignment", 1.0)

        # PP-2 FIX: EWMA smooth the raw alignment to eliminate single-vote discrete jumps.
        # e.g. one TF switching from NEUTRAL→BULLISH flipped alignment 0.33→0.67 instantly.
        alpha = settings.mtf_alignment_ewma_alpha
        if self._mtf_alignment_ema is None:
            self._mtf_alignment_ema = raw_mtf_alignment
        else:
            self._mtf_alignment_ema = alpha * raw_mtf_alignment + (1 - alpha) * self._mtf_alignment_ema
        mtf_alignment = self._mtf_alignment_ema

        # PP-2 FIX: Hysteresis thresholds now come from settings (were hardcoded 0.34/0.38)
        mtf_entry_th = settings.mtf_alignment_damp_entry
        mtf_exit_th = settings.mtf_alignment_damp_exit

        if not self._mtf_damped and mtf_alignment < mtf_entry_th:
            self._mtf_damped = True
            logger.info(f"[AgentG] MTF Damping ACTIVATED: alignment={mtf_alignment:.2f} < {mtf_entry_th}")
        elif self._mtf_damped and mtf_alignment > mtf_exit_th:
            self._mtf_damped = False
            logger.info(f"[AgentG] MTF Damping DEACTIVATED: alignment={mtf_alignment:.2f} > {mtf_exit_th}")

        if self._mtf_damped:
            fused_signal_confidence = fused_signal.confidence * 0.5
            summary.append(f"MTF ALIGN DAMP: alignment={mtf_alignment:.2f} → conf halved.")
        elif mtf_alignment >= 0.67 and premium_state == "BARGAIN":
            # VRP Bargain + MTF fully aligned = best entry condition
            fused_signal_confidence = min(fused_signal.confidence * settings.vrp_bargain_boost, 1.0)
            summary.append(f"VRP BARGAIN BOOST: alignment={mtf_alignment:.2f}, VRP={vrp:.1f}")
        else:
            fused_signal_confidence = fused_signal.confidence

        # Phase 25D — GEX Directional Refinement (Paper 4)
        # GEX < -500M indicates momentum acceleration risk.
        # PP-4 FIX: threshold and boost multipliers moved from magic numbers to settings.
        # Signals aligning with the gamma-induced move should get higher confidence.
        gex_accel_boost = 1.0
        if net_gex_f is not None and net_gex_f < settings.gex_accel_threshold:
            if fused_signal.direction == "BEARISH":
                gex_accel_boost = settings.gex_accel_boost_bearish
                summary.append("GEX ACCEL: Neg Gamma reinforcing Bearish move (Paper 4).")
            elif fused_signal.direction == "BULLISH":
                gex_accel_boost = settings.gex_accel_boost_bullish
                summary.append("GEX ACCEL: Neg Gamma reinforcing Bullish bounce (Short Squeeze).")
        elif net_gex_f is not None and net_gex_f > 800 and fused_signal.direction == "NEUTRAL":
            summary.append("GEX PINNING: Strong Pos Gamma limiting volatility (Paper 2).")

        fused_signal_confidence = min(fused_signal_confidence * gex_accel_boost, 1.0)

        # ── Practice 3: VOL ACCEL SQUEEZE Confidence Boost ────────────────
        # A volume burst (1s vol ≥ 3× 60s avg) in a negative GEX environment signals
        # Dealer delta-hedge exhaustion. Escalate confidence to encourage faster entry.
        # Academic: Muravyev & Pearson (2024/2026) — dealer inventory stress.
        if dealer_squeeze_alert:
            fused_signal_confidence = min(fused_signal_confidence * 1.25, 1.0)
            summary.append("VOL ACCEL SQUEEZE: High volume burst in Neg Gamma → Risk elevated.")
            logger.info(
                "[AgentG.Practice3] VOL ACCEL SQUEEZE: avg_vpin=%.3f dir=%s conf×1.25",
                avg_atm_vpin, fused_signal.direction,
            )
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
        net_charm = None  # Add to b1 schema later if needed

        res = AgentResult(
            agent=self.AGENT_ID,
            signal=signal,
            as_of=agent_a.as_of,
            data={
                "fused_signal": {
                    "direction": fused_signal.direction,
                    "confidence": fused_signal.confidence,
                    "weights": fused_signal.weights,
                    "regime": fused_signal.regime,
                    "iv_regime": fused_signal.iv_regime.value,
                    "gex_intensity": fused_signal.gex_intensity.value,
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
        
        logger.info(f"[L2 AgentG] Final Signal: {res.signal} | Gate Winner Statement: {res.summary}")
        return res

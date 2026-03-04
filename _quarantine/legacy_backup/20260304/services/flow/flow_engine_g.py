"""FlowEngine_G — OI Momentum Flow.

Method G distinguishes opening from closing positions using the change in
Open Interest (ΔOI = OI_now − OI_prev), weighted by the Moneyness-normalised
IV premium and scaled by Turnover.

    Opening + IV rising  → informed directional flow (strong signal)
    Closing + IV falling → position unwind (exit signal)

Mathematical basis:
    FLOW_G_i = ΔOI_i × (IV_i / ATM_IV) × Turnover_i × sign(Type)

    Degradation: if Redis OI cache is unavailable, returns 0 (no signal).

Reference:
    Augustin, Brenner & Hu (2023) "Informed Trading in Options", Mgmt. Science.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.flow_engine import FlowComponentResult, FlowEngineInput
from app.services.cache.oi_snapshot import get_oi_delta
from app.services.system.persistent_oi_store import PersistentOIStore

logger = logging.getLogger(__name__)

_TYPE_SIGN = {"CALL": 1.0, "PUT": -1.0}


class FlowEngineG:
    """OI Momentum Flow engine (Method G)."""

    async def compute(
        self,
        inputs: list[FlowEngineInput],
        redis: Any | None = None,
        oi_store: PersistentOIStore | None = None,
        date_str: str | None = None,
    ) -> list[FlowComponentResult]:
        """Compute OI-momentum-weighted flow for each strike.

        Args:
            inputs: Validated per-strike input contracts.
            redis:  Async Redis client.  If None, G-engine yields all zeros.

        Returns:
            List of FlowComponentResult.
        """
        results = []

        if not redis:
            logger.warning("[FlowEngineG] Redis unavailable — returning zero flows (graceful degradation)")
            return [
                FlowComponentResult(
                    symbol=inp.symbol,
                    strike=inp.strike,
                    option_type=inp.option_type,
                    flow_value=0.0,
                    is_valid=False,
                    failure_reason="redis_unavailable",
                )
                for inp in inputs
            ]

        for inp in inputs:
            try:
                if inp.volume <= 0 or inp.turnover <= 0:
                    results.append(FlowComponentResult(
                        symbol=inp.symbol,
                        strike=inp.strike,
                        option_type=inp.option_type,
                        flow_value=0.0,
                        is_valid=False,
                        failure_reason="zero volume/turnover",
                    ))
                    continue

                delta_oi = await get_oi_delta(redis, inp.symbol, inp.open_interest, date_str=date_str)

                # Fallback to Persistent Local Store if Redis returns 0 (miss or same value)
                if delta_oi == 0 and oi_store:
                    baseline = oi_store.get_baseline(date_str or "")
                    prev_oi = baseline.get(inp.symbol)
                    if prev_oi is not None:
                        delta_oi = inp.open_interest - prev_oi
                        logger.debug(f"[FlowEngineG] Persistent fallback for {inp.symbol}: Δ{delta_oi}")

                # If we still have no history, treat as neutral
                if delta_oi == 0:
                    results.append(FlowComponentResult(
                        symbol=inp.symbol,
                        strike=inp.strike,
                        option_type=inp.option_type,
                        flow_value=0.0,
                        is_valid=True,
                        failure_reason="no_oi_history",
                    ))
                    continue

                # Moneyness-normalised IV premium
                iv_norm = (inp.implied_volatility / inp.atm_iv) if inp.atm_iv > 0 else 1.0
                type_sign = _TYPE_SIGN.get(inp.option_type, 1.0)

                flow_g = delta_oi * iv_norm * inp.turnover * type_sign

                results.append(FlowComponentResult(
                    symbol=inp.symbol,
                    strike=inp.strike,
                    option_type=inp.option_type,
                    flow_value=flow_g,
                ))

            except Exception as exc:
                logger.warning(f"[FlowEngineG] Error for {inp.symbol}: {exc}")
                results.append(FlowComponentResult(
                    symbol=inp.symbol,
                    strike=inp.strike,
                    option_type=inp.option_type,
                    flow_value=0.0,
                    is_valid=False,
                    failure_reason=str(exc),
                ))

        return results

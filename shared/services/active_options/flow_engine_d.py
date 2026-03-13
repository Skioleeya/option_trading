"""FlowEngine_D - Gamma Imbalance Flow.

This engine is a research heuristic / public-data proxy. It combines public
volume with gamma-derived sensitivity to approximate structural hedging
pressure. It must not be described as a unified academic exact formula or as
dealer inventory truth.

Composite formula:
    FLOW_D_i = Volume_i x Gamma_i x Spot^2 x 0.01 x sign(Type)

See `shared.contracts.metric_semantics:get_metric_semantics("FLOW_D")` for the
canonical provenance record.
"""

from __future__ import annotations

import logging
from typing import Any

from shared.models.flow_engine import FlowComponentResult, FlowEngineInput

logger = logging.getLogger(__name__)

_SIGN = {"CALL": 1.0, "PUT": -1.0}


class FlowEngineD:
    """Gamma imbalance flow engine using a public-data proxy heuristic."""

    def compute(
        self,
        inputs: list[FlowEngineInput],
    ) -> list[FlowComponentResult]:
        """Compute Gamma-based flow for each strike.

        Args:
            inputs: Validated per-strike input contracts.

        Returns:
            List of FlowComponentResult, one per strike.
        """
        results = []
        for inp in inputs:
            try:
                if inp.volume <= 0 or inp.gamma <= 0 or inp.spot <= 0:
                    results.append(FlowComponentResult(
                        symbol=inp.symbol,
                        strike=inp.strike,
                        option_type=inp.option_type,
                        flow_value=0.0,
                        is_valid=False,
                        failure_reason="zero volume/gamma/spot",
                    ))
                    continue

                # GEX-style: dealer must hedge with Spot^2 x Gamma x Volume x Multiplier(100) x 0.01
                raw = inp.volume * inp.gamma * (inp.spot ** 2) * 100 * 0.01
                flow_d = raw * _SIGN.get(inp.option_type, 1.0)

                results.append(FlowComponentResult(
                    symbol=inp.symbol,
                    strike=inp.strike,
                    option_type=inp.option_type,
                    flow_value=flow_d,
                ))

            except Exception as exc:
                logger.warning(f"[FlowEngineD] Error for {inp.symbol}: {exc}")
                results.append(FlowComponentResult(
                    symbol=inp.symbol,
                    strike=inp.strike,
                    option_type=inp.option_type,
                    flow_value=0.0,
                    is_valid=False,
                    failure_reason=str(exc),
                ))

        return results

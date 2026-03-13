"""FlowEngine_E - Vanna x Delta-IV Flow.

This engine is a research heuristic / public-data proxy. It combines public
IV premium and vanna sensitivity into a directional composite, but it must not
be described as a unified academic exact formula.

Composite formula:
    FLOW_E_i = Volume_i x |Vanna_i| x (IV_i - HV_i) x sign(DeltaIV x Type)

    sign:
        If IV > HV (premium):  sign = +1 for CALL, -1 for PUT
        If IV <= HV (discount): sign is inverted

See `shared.contracts.metric_semantics:get_metric_semantics("FLOW_E")` for the
canonical provenance record.
"""

from __future__ import annotations

import logging

from shared.models.flow_engine import FlowComponentResult, FlowEngineInput

logger = logging.getLogger(__name__)

_TYPE_SIGN = {"CALL": 1.0, "PUT": -1.0}


class FlowEngineE:
    """Vanna x Delta-IV flow engine using a research heuristic."""

    def compute(
        self,
        inputs: list[FlowEngineInput],
    ) -> list[FlowComponentResult]:
        """Compute Vanna-weighted IV premium flow for each strike.

        Returns zero-valued (but valid) results when IV ~= HV to avoid
        injecting noise into the composite FLOW_DEG score.
        """
        results = []
        for inp in inputs:
            try:
                if inp.volume <= 0:
                    results.append(FlowComponentResult(
                        symbol=inp.symbol,
                        strike=inp.strike,
                        option_type=inp.option_type,
                        flow_value=0.0,
                        is_valid=False,
                        failure_reason="zero volume",
                    ))
                    continue

                delta_iv = inp.implied_volatility - inp.historical_volatility

                # If both IV and HV are zero, ensure no division or signal
                if inp.implied_volatility == 0 and inp.historical_volatility == 0:
                    results.append(FlowComponentResult(
                        symbol=inp.symbol,
                        strike=inp.strike,
                        option_type=inp.option_type,
                        flow_value=0.0,
                        is_valid=True,
                        failure_reason="IV=HV=0, no signal",
                    ))
                    continue

                # Directional sign: premium buyer on CALL is bullish
                type_sign = _TYPE_SIGN.get(inp.option_type, 1.0)
                iv_sign = 1.0 if delta_iv >= 0 else -1.0
                direction = type_sign * iv_sign

                # Weight by volume and multiplier (100)
                flow_e = inp.volume * 100 * abs(inp.vanna) * abs(delta_iv) * direction

                results.append(FlowComponentResult(
                    symbol=inp.symbol,
                    strike=inp.strike,
                    option_type=inp.option_type,
                    flow_value=flow_e,
                ))

            except Exception as exc:
                logger.warning(f"[FlowEngineE] Error for {inp.symbol}: {exc}")
                results.append(FlowComponentResult(
                    symbol=inp.symbol,
                    strike=inp.strike,
                    option_type=inp.option_type,
                    flow_value=0.0,
                    is_valid=False,
                    failure_reason=str(exc),
                ))

        return results

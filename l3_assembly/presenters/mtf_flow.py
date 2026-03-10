"""l3_assembly.presenters.mtf_flow — MTFFlowPresenterV2.

Physics-only MTF contract:
- state
- relative_displacement
- pressure_gradient
- distance_to_vacuum
- kinetic_level
"""

from __future__ import annotations

import math
from typing import Any

from l3_assembly.events.payload_events import MTFFlowState


class MTFFlowPresenterV2:
    """Strongly-typed MTF Flow presenter (no UI style tokens)."""

    @classmethod
    def build(cls, mtf_consensus: dict[str, Any]) -> MTFFlowState:
        raw = mtf_consensus if isinstance(mtf_consensus, dict) else {}
        tf_map = raw.get("timeframes", {})
        if not isinstance(tf_map, dict):
            tf_map = {}
        return MTFFlowState(
            m1=cls._normalize_tf(tf_map.get("1m")),
            m5=cls._normalize_tf(tf_map.get("5m")),
            m15=cls._normalize_tf(tf_map.get("15m")),
        )

    @staticmethod
    def _normalize_tf(raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            return MTFFlowState.zero_state().m1

        state_raw = raw.get("state")
        if state_raw == 1 or state_raw == -1 or state_raw == 0:
            state = int(state_raw)
        elif state_raw == "1" or state_raw == "-1" or state_raw == "0":
            state = int(state_raw)
        else:
            state = 0

        return {
            "state": state,
            "relative_displacement": MTFFlowPresenterV2._to_finite(raw.get("relative_displacement")),
            "pressure_gradient": MTFFlowPresenterV2._to_finite(raw.get("pressure_gradient")),
            "distance_to_vacuum": max(0.0, MTFFlowPresenterV2._to_finite(raw.get("distance_to_vacuum"))),
            "kinetic_level": MTFFlowPresenterV2._clamp01(raw.get("kinetic_level", 0.0)),
        }

    @staticmethod
    def _to_finite(value: Any, default: float = 0.0) -> float:
        try:
            out = float(value)
        except (TypeError, ValueError):
            return default
        if not math.isfinite(out):
            return default
        return out

    @staticmethod
    def _clamp01(value: Any) -> float:
        out = MTFFlowPresenterV2._to_finite(value, 0.0)
        if out < 0.0:
            return 0.0
        if out > 1.0:
            return 1.0
        return out

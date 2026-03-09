"""l3_assembly.assembly.ui_state_tracker — Contract-only UI state mapper.

Consumes L1/L2 output contracts and emits UI-oriented metrics without importing
L1 tracker/analysis implementation modules.
"""

from __future__ import annotations

from collections.abc import Iterable
import math
from types import SimpleNamespace
from typing import Any

from shared.config import settings
from shared.system.tactical_triad_logic import (
    classify_vrp_state,
    compute_vrp,
    normalize_svol_state,
    resolve_svol_fields,
)


class UIStateTracker:
    """Maps EnrichedSnapshot + DecisionOutput contracts to UI metrics."""

    async def set_redis_client(self, client: Any) -> None:
        """Compatibility no-op. UI tracker is contract-only and stateless."""
        _ = client
        return None

    def tick(self, snapshot: Any, decision: Any) -> dict[str, Any]:
        """Build UI metrics from contract fields only."""
        agg = self._extract_aggregates(snapshot)
        if agg is None:
            return {}

        spot = self._to_float(self._get(agg, "spot", self._get(snapshot, "spot", 0.0)), default=0.0)
        atm_iv = self._to_float(self._get(agg, "atm_iv", 0.0), default=0.0)
        net_charm = self._to_float(self._get(agg, "net_charm", 0.0), default=0.0)

        micro_state = self._extract_micro_state(snapshot)

        vanna_raw = micro_state.get("vanna_flow_result") or micro_state.get("vanna_flow")
        wall_raw = micro_state.get("wall_migration")
        mtf_raw = micro_state.get("mtf_consensus")
        iv_velocity = micro_state.get("iv_velocity")

        vanna_view = self._to_vanna_view(vanna_raw)
        if vanna_view is None:
            vanna_view = SimpleNamespace(state=SimpleNamespace(value="UNAVAILABLE"), correlation=None, gex_regime=SimpleNamespace(value="NEUTRAL"))

        vanna_state_raw = getattr(getattr(vanna_view, "state", None), "value", "UNAVAILABLE")
        vanna_state_str = normalize_svol_state(vanna_state_raw)
        gex_regime_str = getattr(getattr(vanna_view, "gex_regime", None), "value", "NEUTRAL")

        svol_corr, svol_state = resolve_svol_fields(vanna_view)

        wall_payload = self._to_wall_payload(wall_raw)

        mtf_consensus = self._extract_snapshot_mtf_consensus({"mtf_consensus": mtf_raw})
        if mtf_consensus is None:
            mtf_consensus = {
                "timeframes": {},
                "alignment": 0.0,
                "consensus": "NEUTRAL",
                "strength": 0.0,
            }

        vrp = compute_vrp(atm_iv, getattr(settings, "vrp_baseline_hv", 13.5))
        vrp_state = classify_vrp_state(
            vrp,
            getattr(settings, "vrp_cheap_threshold", -2.0),
            getattr(settings, "vrp_expensive_threshold", 2.0),
            getattr(settings, "vrp_trap_threshold", 5.0),
        )

        skew_dynamics = self._extract_skew_dynamics(decision)
        momentum_direction = self._extract_momentum(decision)

        return {
            "wall_migration_data": wall_payload,
            "mtf_consensus": mtf_consensus,
            "vanna_state": vanna_state_str,
            "gex_regime": str(gex_regime_str),
            "vrp": vrp,
            "vrp_state": vrp_state,
            "net_charm": net_charm,
            "skew_dynamics": skew_dynamics,
            "momentum": momentum_direction,
            "svol_corr": svol_corr,
            "svol_state": svol_state,
            "iv_velocity": iv_velocity,
            "micro_structure": {"micro_structure_state": micro_state},
            "spot": spot,
        }

    @classmethod
    def _extract_aggregates(cls, snapshot: Any) -> Any | None:
        if hasattr(snapshot, "aggregates"):
            return snapshot.aggregates
        if isinstance(snapshot, dict):
            return snapshot.get("aggregates", snapshot)
        return None

    @classmethod
    def _extract_micro_state(cls, snapshot: Any) -> dict[str, Any]:
        if hasattr(snapshot, "microstructure") and snapshot.microstructure:
            ms = snapshot.microstructure
            if hasattr(ms, "model_dump"):
                dumped = ms.model_dump()
                if isinstance(dumped, dict):
                    return dumped
            if isinstance(ms, dict):
                return dict(ms)

            return {
                "iv_velocity": getattr(ms, "iv_velocity", None),
                "wall_migration": getattr(ms, "wall_migration", None),
                "vanna_flow_result": getattr(ms, "vanna_flow_result", None),
                "mtf_consensus": getattr(ms, "mtf_consensus", None),
                "volume_imbalance": getattr(ms, "volume_imbalance", None),
                "jump_detection": getattr(ms, "jump_detection", None),
                "dealer_squeeze_alert": getattr(ms, "dealer_squeeze_alert", False),
                "iv_confidence": getattr(ms, "iv_confidence", 0.0),
                "wall_confidence": getattr(ms, "wall_confidence", 0.0),
                "vanna_confidence": getattr(ms, "vanna_confidence", 0.0),
            }

        if isinstance(snapshot, dict):
            ms_raw = snapshot.get("micro_structure", {}).get("micro_structure_state") or snapshot.get("microstructure", {})
            if isinstance(ms_raw, dict):
                return dict(ms_raw)
        return {}

    @classmethod
    def _to_vanna_view(cls, raw: Any) -> Any | None:
        if raw is None:
            return None
        if hasattr(raw, "state") and hasattr(raw, "correlation"):
            return raw
        if not isinstance(raw, dict):
            return None

        state_raw = raw.get("state", "UNAVAILABLE")
        if isinstance(state_raw, dict):
            state_raw = state_raw.get("value", "UNAVAILABLE")

        gex_regime_raw = raw.get("gex_regime", "NEUTRAL")
        if isinstance(gex_regime_raw, dict):
            gex_regime_raw = gex_regime_raw.get("value", "NEUTRAL")

        return SimpleNamespace(
            state=SimpleNamespace(value=str(state_raw)),
            correlation=raw.get("correlation"),
            gex_regime=SimpleNamespace(value=str(gex_regime_raw)),
        )

    @classmethod
    def _to_wall_payload(cls, raw: Any) -> dict[str, Any]:
        if raw is None:
            return {}

        if hasattr(raw, "model_dump"):
            dumped = raw.model_dump()
            if isinstance(dumped, dict):
                raw = dumped

        if not isinstance(raw, dict):
            return {}

        call_state = raw.get("call_wall_state")
        put_state = raw.get("put_wall_state")
        call_history = cls._normalize_wall_history(raw.get("call_wall_history"))
        put_history = cls._normalize_wall_history(raw.get("put_wall_history"))

        if call_state is None and put_state is None and not call_history and not put_history:
            return {}

        return {
            "call_wall_state": str(call_state) if call_state is not None else "UNAVAILABLE",
            "put_wall_state": str(put_state) if put_state is not None else "UNAVAILABLE",
            "call_wall_history": call_history,
            "put_wall_history": put_history,
        }

    @staticmethod
    def _normalize_wall_history(value: Any) -> list[float | None]:
        if value is None or isinstance(value, (str, bytes)):
            return []
        if not isinstance(value, Iterable):
            return []

        out: list[float | None] = []
        for item in value:
            if item is None:
                out.append(None)
                continue
            try:
                num = float(item)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(num) or num <= 0.0:
                out.append(None)
            else:
                out.append(num)
        return out

    @classmethod
    def _extract_skew_dynamics(cls, decision: Any) -> dict[str, Any]:
        features = getattr(decision, "feature_vector", {}) if decision else {}
        if not isinstance(features, dict):
            features = {}

        valid_flag = cls._to_float(features.get("skew_25d_valid", 0.0), default=0.0)
        if valid_flag < 0.5:
            return {
                "skew_value": None,
                "skew_state": "UNAVAILABLE",
            }

        skew_val = cls._to_float(features.get("skew_25d_normalized", 0.0), default=0.0)

        skew_state = "NEUTRAL"
        if skew_val < getattr(settings, "skew_speculative_max", -0.10):
            skew_state = "SPECULATIVE"
        elif skew_val > getattr(settings, "skew_defensive_min", 0.15):
            skew_state = "DEFENSIVE"

        return {
            "skew_value": skew_val,
            "skew_state": skew_state,
        }

    @classmethod
    def _extract_momentum(cls, decision: Any) -> str:
        if not decision or not hasattr(decision, "signal_summary"):
            return "NEUTRAL"
        summary = getattr(decision, "signal_summary", {})
        if not isinstance(summary, dict):
            return "NEUTRAL"
        mom_sig = summary.get("momentum_signal", "NEUTRAL")
        if isinstance(mom_sig, dict):
            return str(mom_sig.get("direction", "NEUTRAL"))
        return str(mom_sig)

    @staticmethod
    def _get(obj: Any, attr: str, default: Any = 0.0) -> Any:
        if hasattr(obj, attr):
            return getattr(obj, attr)
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return default

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            out = float(value)
        except (TypeError, ValueError):
            return default
        if not math.isfinite(out):
            return default
        return out

    @staticmethod
    def _extract_snapshot_mtf_consensus(micro_state: Any) -> dict[str, Any] | None:
        """Prefer L1 microstructure mtf_consensus when available and structurally valid."""
        if not isinstance(micro_state, dict):
            return None
        candidate = micro_state.get("mtf_consensus")
        if not isinstance(candidate, dict):
            return None

        timeframes = candidate.get("timeframes")
        if not isinstance(timeframes, dict):
            return None

        consensus = str(candidate.get("consensus", "NEUTRAL"))
        strength_raw = candidate.get("strength", 0.0)
        alignment_raw = candidate.get("alignment", 0.0)
        try:
            strength = float(strength_raw)
            alignment = float(alignment_raw)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(strength) or not math.isfinite(alignment):
            return None

        out = dict(candidate)
        out["consensus"] = consensus
        out["strength"] = strength
        out["alignment"] = alignment
        out["timeframes"] = dict(timeframes)
        return out

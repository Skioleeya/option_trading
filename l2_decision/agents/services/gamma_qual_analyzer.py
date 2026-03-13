"""GammaQualAnalyzer — qualitative gamma interpretation for L2.

Design contract:
- Quantitative gamma/greeks computation belongs to L1.
- L2 only consumes L1 aggregate contracts and produces qualitative/compatibility views.
"""

from __future__ import annotations

import math
from typing import Any


class GammaQualAnalyzer:
    """Consume L1 aggregate contract and map it to L2 qualitative outputs.

    This service preserves L1 proxy semantics. It does not infer hidden dealer
    inventory or upgrade wall/GEX fields into dealer-truth statements.
    """

    def summarize(
        self,
        aggregate_greeks: dict[str, Any] | Any,
        spot: float,
    ) -> dict[str, Any]:
        """Build qualitative gamma summary from L1 aggregate proxy fields."""
        net_gex = self._to_float(self._agg_get(aggregate_greeks, "net_gex", 0.0), default=0.0)
        call_wall = self._finite_or_none(self._agg_get(aggregate_greeks, "call_wall"))
        put_wall = self._finite_or_none(self._agg_get(aggregate_greeks, "put_wall"))
        legacy_flip_level = self._finite_or_none(self._agg_get(aggregate_greeks, "flip_level"))
        flip_level_cumulative = self._finite_or_none(self._agg_get(aggregate_greeks, "flip_level_cumulative"))
        zero_gamma_level = self._finite_or_none(self._agg_get(aggregate_greeks, "zero_gamma_level"))
        total_call_gex = self._to_float(self._agg_get(aggregate_greeks, "total_call_gex", 0.0), default=0.0)
        total_put_gex = self._to_float(self._agg_get(aggregate_greeks, "total_put_gex", 0.0), default=0.0)
        net_vanna = self._to_float(
            self._agg_get_first(aggregate_greeks, ("net_vanna_raw_sum", "net_vanna"), 0.0),
            default=0.0,
        )
        net_charm = self._to_float(
            self._agg_get_first(aggregate_greeks, ("net_charm_raw_sum", "net_charm"), 0.0),
            default=0.0,
        )
        atm_iv = self._finite_or_none(self._agg_get(aggregate_greeks, "atm_iv"))

        per_strike_raw = self._agg_get(aggregate_greeks, "per_strike_gex", [])
        per_strike_gex = self._normalize_per_strike(per_strike_raw)

        if zero_gamma_level is None:
            zero_gamma_level = legacy_flip_level
        if flip_level_cumulative is None:
            flip_level_cumulative = legacy_flip_level

        gamma_flip = self._infer_gamma_flip(
            spot=self._finite_or_none(spot),
            net_gex=net_gex,
            zero_gamma_level=zero_gamma_level,
        )

        return {
            "net_gex": net_gex,
            "put_wall": put_wall,
            "call_wall": call_wall,
            "gamma_flip_level": zero_gamma_level,
            "flip_level_cumulative": flip_level_cumulative,
            "gamma_flip": gamma_flip,
            "per_strike_gex": per_strike_gex,
            "total_call_gex": total_call_gex,
            "total_put_gex": total_put_gex,
            "net_vanna_raw_sum": net_vanna,
            "net_vanna": net_vanna,
            "net_charm_raw_sum": net_charm,
            "net_charm": net_charm,
            "atm_iv": atm_iv,
            "spot": self._to_float(spot, default=0.0),
        }

    def build_gamma_profile(
        self,
        per_strike_gex: list[dict[str, Any]],
        spot: float,
    ) -> list[dict[str, float]]:
        """Compatibility gamma profile view derived from L1 per-strike output.

        This does not re-price options and does not recompute gamma.
        It simply reshapes the per-strike OI-based proxy profile for legacy consumers.
        """
        _ = spot  # Keep signature stable for legacy callers.
        profile: list[dict[str, float]] = []
        for row in per_strike_gex:
            if not isinstance(row, dict):
                continue
            strike = self._finite_or_none(row.get("strike"))
            net_gex = self._finite_or_none(row.get("net_gex"))
            if strike is None or net_gex is None:
                continue
            profile.append({"price": round(strike, 2), "net_gex": float(net_gex)})

        profile.sort(key=lambda x: x["price"])
        return profile

    @staticmethod
    def _agg_get(aggregate_greeks: dict[str, Any] | Any, key: str, default: Any = None) -> Any:
        if isinstance(aggregate_greeks, dict):
            return aggregate_greeks.get(key, default)
        return getattr(aggregate_greeks, key, default)

    @classmethod
    def _agg_get_first(
        cls,
        aggregate_greeks: dict[str, Any] | Any,
        keys: tuple[str, ...],
        default: Any = None,
    ) -> Any:
        for key in keys:
            value = cls._agg_get(aggregate_greeks, key, None)
            if value is not None:
                return value
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

    @classmethod
    def _finite_or_none(cls, value: Any) -> float | None:
        try:
            out = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(out):
            return None
        return out

    @classmethod
    def _normalize_per_strike(cls, raw: Any) -> list[dict[str, float]]:
        if not isinstance(raw, list):
            return []

        out: list[dict[str, float]] = []
        for row in raw:
            if not isinstance(row, dict):
                continue

            strike = cls._finite_or_none(row.get("strike"))
            call_gex = cls._finite_or_none(row.get("call_gex"))
            put_gex = cls._finite_or_none(row.get("put_gex"))
            net_gex = cls._finite_or_none(row.get("net_gex"))

            if strike is None:
                continue

            out.append(
                {
                    "strike": strike,
                    "call_gex": 0.0 if call_gex is None else call_gex,
                    "put_gex": 0.0 if put_gex is None else put_gex,
                    "net_gex": 0.0 if net_gex is None else net_gex,
                }
            )

        out.sort(key=lambda x: x["strike"])
        return out

    @staticmethod
    def _infer_gamma_flip(
        *,
        spot: float | None,
        net_gex: float,
        zero_gamma_level: float | None,
    ) -> bool:
        """Infer whether the market is in negative-gamma regime.

        Prefer zero-gamma proxy location when available, otherwise fall back to
        aggregate net-GEX proxy sign.
        """
        if (
            spot is not None
            and spot > 0.0
            and zero_gamma_level is not None
            and zero_gamma_level > 0.0
        ):
            return bool(spot < zero_gamma_level)
        return bool(net_gex < 0.0)

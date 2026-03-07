"""Greeks Extractor — L2 qualitative bridge over L1 quantitative contracts.

Design contract:
- L1 is the source of truth for gamma/greeks quantitative computation.
- L2 consumes L1 aggregate output and only performs qualitative mapping/bridging.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from l2_decision.agents.services.gamma_qual_analyzer import GammaQualAnalyzer


logger = logging.getLogger(__name__)


class GreeksExtractor:
    """Maps L1 aggregate greeks to L2-compatible payload fields."""

    def __init__(self) -> None:
        self._gamma_qual_analyzer = GammaQualAnalyzer()
        self._last_result: dict[str, Any] | None = None

    def compute(
        self,
        chain: list[dict[str, Any]],
        spot: float,
        as_of: datetime | None = None,
        aggregate_greeks: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build L2-facing greeks payload from L1 aggregate contract."""
        if as_of is None:
            as_of = datetime.now(ZoneInfo("US/Eastern"))

        if spot <= 0:
            logger.warning("[GreeksExtractor] Invalid spot <= 0")
            return self._empty_result()

        if not aggregate_greeks:
            logger.warning("[GreeksExtractor] Missing aggregate_greeks; returning degraded qualitative payload")
            degraded = self._empty_result()
            degraded["atm_iv"] = self._extract_atm_iv(chain, spot)
            degraded["spy_atm_iv"] = degraded["atm_iv"]
            degraded["skew_25d"] = self._extract_skew_ivs(chain)
            degraded["as_of"] = as_of.isoformat()
            self._last_result = degraded
            return degraded

        summary = self._gamma_qual_analyzer.summarize(aggregate_greeks, spot)
        per_strike_gex = summary.get("per_strike_gex", [])
        gamma_profile = self._gamma_qual_analyzer.build_gamma_profile(per_strike_gex, spot)

        atm_iv = summary.get("atm_iv")
        if atm_iv is None or atm_iv <= 0:
            atm_iv = self._extract_atm_iv(chain, spot)

        result = {
            "net_gex": summary.get("net_gex", 0.0),
            "gamma_walls": {
                "call_wall": summary.get("call_wall"),
                "put_wall": summary.get("put_wall"),
            },
            "gamma_flip_level": summary.get("gamma_flip_level"),
            "gamma_flip": summary.get("gamma_flip", False),
            "atm_iv": atm_iv,
            "spy_atm_iv": atm_iv,
            "skew_25d": self._extract_skew_ivs(chain),
            "charm_exposure": summary.get("net_charm", 0.0),
            "vanna_exposure": summary.get("net_vanna", 0.0),
            "gamma_profile": gamma_profile,
            "per_strike_gex": per_strike_gex,
            "total_call_gex": summary.get("total_call_gex", 0.0),
            "total_put_gex": summary.get("total_put_gex", 0.0),
            "otm_call_vol": aggregate_greeks.get("otm_call_vol", 0),
            "otm_put_vol": aggregate_greeks.get("otm_put_vol", 0),
            "total_chain_vol": aggregate_greeks.get("total_chain_vol", 0),
            "as_of": as_of.isoformat(),
        }

        self._last_result = result
        return result

    def _extract_atm_iv(
        self,
        chain: list[dict[str, Any]],
        spot: float,
    ) -> float | None:
        """Extract ATM implied volatility from the nearest call option."""
        best_call_iv = None
        min_distance = float("inf")

        for opt in chain:
            opt_type = str(opt.get("option_type", opt.get("type", ""))).upper()
            if opt_type not in ("CALL", "C"):
                continue

            strike = opt.get("strike", 0)
            iv = opt.get("implied_volatility", 0)

            if strike <= 0 or not iv or iv <= 0:
                continue

            distance = abs(strike - spot)
            if distance < min_distance:
                min_distance = distance
                best_call_iv = iv

        return best_call_iv

    def _extract_skew_ivs(self, chain: list[dict[str, Any]]) -> dict[str, float | None]:
        """Extract IVs for 25-delta put and call for skew diagnostics."""
        put_25d_iv = None
        call_25d_iv = None

        min_put_delta_diff = float("inf")
        min_call_delta_diff = float("inf")

        for opt in chain:
            try:
                delta = abs(float(opt.get("delta", 0) or 0))
                iv = float(opt.get("implied_volatility", 0) or 0)
                opt_type = str(opt.get("option_type", opt.get("type", ""))).upper()

                if iv <= 0 or delta <= 0:
                    continue

                diff = abs(delta - 0.25)

                if opt_type in ("PUT", "P"):
                    if diff < min_put_delta_diff:
                        min_put_delta_diff = diff
                        put_25d_iv = iv
                elif opt_type in ("CALL", "C"):
                    if diff < min_call_delta_diff:
                        min_call_delta_diff = diff
                        call_25d_iv = iv
            except (ValueError, TypeError):
                continue

        return {
            "put_25d_iv": put_25d_iv,
            "call_25d_iv": call_25d_iv,
        }

    def _empty_result(self) -> dict[str, Any]:
        """Return empty result structure."""
        return {
            "net_gex": 0.0,
            "gamma_walls": {"call_wall": None, "put_wall": None},
            "gamma_flip_level": None,
            "gamma_flip": False,
            "atm_iv": None,
            "spy_atm_iv": None,
            "charm_exposure": 0.0,
            "vanna_exposure": 0.0,
            "gamma_profile": [],
            "per_strike_gex": [],
            "total_call_gex": 0.0,
            "total_put_gex": 0.0,
            "otm_call_vol": 0,
            "otm_put_vol": 0,
            "total_chain_vol": 0,
            "skew_25d": {"put_25d_iv": None, "call_25d_iv": None},
            "as_of": None,
        }

    def get_diagnostics(self) -> dict[str, Any]:
        """Return diagnostic info for debug endpoint."""
        if self._last_result:
            return {
                "has_result": True,
                "net_gex": self._last_result.get("net_gex"),
                "call_wall": self._last_result.get("gamma_walls", {}).get("call_wall"),
                "put_wall": self._last_result.get("gamma_walls", {}).get("put_wall"),
                "flip_level": self._last_result.get("gamma_flip_level"),
                "atm_iv": self._last_result.get("atm_iv"),
            }
        return {"has_result": False}

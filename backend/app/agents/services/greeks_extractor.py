"""Greeks Extractor — BSM Greeks computation and chain processing.

Extracts and computes Greeks for the option chain:
- Processes raw option chain data from Longport API
- Computes Net GEX via GammaAnalyzer
- Aggregates Charm and Vanna exposures
- Determines ATM IV and gamma walls
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.agents.services.gamma_analyzer import GammaAnalyzer
from app.config import settings


logger = logging.getLogger(__name__)


class GreeksExtractor:
    """Extracts and computes Greeks from option chain data.

    Orchestrates GammaAnalyzer for GEX computations and provides
    aggregated metrics for the decision agents.
    """

    def __init__(self) -> None:
        self._gamma_analyzer = GammaAnalyzer()
        self._last_result: dict[str, Any] | None = None

    def compute(
        self,
        chain: list[dict[str, Any]],
        spot: float,
        as_of: datetime | None = None,
    ) -> dict[str, Any]:
        """Compute all Greeks metrics from option chain.

        Args:
            chain: List of option dicts with greeks data
            spot: Current spot price
            as_of: Timestamp of the data

        Returns:
            Dict with net_gex, gamma_walls, atm_iv, charm_exposure,
            vanna_exposure, gamma_profile, etc.
        """
        if as_of is None:
            as_of = datetime.now(ZoneInfo("US/Eastern"))

        if not chain or spot <= 0:
            logger.warning("[GreeksExtractor] Empty chain or invalid spot")
            return self._empty_result()

        logger.warning(
            f"[GreeksExtractor] Chain length={len(chain)}, spot={spot}, "
            f"net_gex={self._gamma_analyzer.compute_net_gex(chain, spot)['net_gex']}"
        )

        # Log sample call for diagnostics
        if chain:
            logger.warning(f"[GreeksExtractor] Sample Raw Option keys: {chain[0].keys()}")
            logger.warning(f"[GreeksExtractor] Sample Raw Option: {chain[0]}")
        else:
            logger.warning("[GreeksExtractor] Chain is empty")

        # 1. Core GEX computation
        gex_result = self._gamma_analyzer.compute_net_gex(chain, spot)

        # 2. ATM IV extraction
        atm_iv = self._extract_atm_iv(chain, spot)

        # 3. Charm exposure
        charm_exposure = self._gamma_analyzer.compute_net_charm(chain)

        # 4. Vanna exposure
        vanna_exposure = self._gamma_analyzer.compute_net_vanna(chain, spot)

        # 5. Gamma profile (for visualization)
        gamma_profile = self._gamma_analyzer.compute_gamma_profile(chain, spot)

        result = {
            "net_gex": gex_result["net_gex"],
            "gamma_walls": {
                "call_wall": gex_result["call_wall"],
                "put_wall": gex_result["put_wall"],
            },
            "gamma_flip_level": gex_result["gamma_flip_level"],
            "gamma_flip": gex_result["gamma_flip"],
            "atm_iv": atm_iv,
            "spy_atm_iv": atm_iv,  # Alias for pure SPY IV architecture
            "skew_25d": self._extract_skew_ivs(chain),
            "charm_exposure": charm_exposure,
            "vanna_exposure": vanna_exposure,
            "gamma_profile": gamma_profile,
            "per_strike_gex": gex_result["per_strike_gex"],
            "total_call_gex": gex_result.get("total_call_gex", 0),
            "total_put_gex": gex_result.get("total_put_gex", 0),
            "as_of": as_of.isoformat(),
        }

        self._last_result = result
        return result

    def _extract_atm_iv(
        self,
        chain: list[dict[str, Any]],
        spot: float,
    ) -> float | None:
        """Extract ATM implied volatility.

        Finds the call option closest to spot and returns its IV.
        """
        best_call_iv = None
        min_distance = float("inf")

        for opt in chain:
            opt_type = opt.get("option_type", opt.get("type", "")).upper()
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

        # Convert to percentage if needed (some APIs return as decimal)
        if best_call_iv is not None and best_call_iv < 1.0:
            best_call_iv *= 100.0

        return best_call_iv

    def _extract_skew_ivs(self, chain: list[dict[str, Any]]) -> dict[str, float | None]:
        """Extract IVs for 25-delta Put and Call.
        
        Used for Skew Dynamic analysis: (PutIV - CallIV) / ATM_IV.
        """
        put_25d_iv = None
        call_25d_iv = None
        
        min_put_delta_diff = float("inf")
        min_call_delta_diff = float("inf")

        for opt in chain:
            try:
                delta = abs(float(opt.get("delta", 0) or 0))
                iv = float(opt.get("implied_volatility", 0) or 0)
                opt_type = opt.get("option_type", opt.get("type", "")).upper()

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

        # Normalized to percentages
        if put_25d_iv and put_25d_iv < 1.0: put_25d_iv *= 100.0
        if call_25d_iv and call_25d_iv < 1.0: call_25d_iv *= 100.0

        return {
            "put_25d_iv": put_25d_iv,
            "call_25d_iv": call_25d_iv
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

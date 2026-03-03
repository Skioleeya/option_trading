"""Gamma Analyzer — Core GEX computation engine.

Calculates:
1. Per-strike GEX (Call GEX and Put GEX)
2. Net GEX (aggregate)
3. Put Wall (max |Put GEX| strike)
4. Call Wall (max |Call GEX| strike)
5. Gamma Flip (zero-crossing of Net GEX curve, interpolated nearest to spot)
6. Gamma Profile (GEX curve across price range)
7. Net Vanna exposure
"""

from __future__ import annotations

import math
from typing import Any

from app.config import settings


class GammaAnalyzer:
    """Core GEX (Gamma Exposure) computation engine.

    GEX Formula per strike:
        GEX_i = Gamma_i × OI_i × Spot² × ContractMultiplier × 0.01
        - Call GEX is positive (dealers long gamma on calls)
        - Put GEX is negative (dealers short gamma on puts)

    Net GEX = sum(Call_GEX) + sum(Put_GEX)  [in dollars, converted to Millions]
    """

    # =========================================================================
    # Core GEX Computation
    # =========================================================================

    def compute_net_gex(
        self,
        chain: list[dict[str, Any]],
        spot: float,
    ) -> dict[str, Any]:
        """Compute Net GEX, Put Wall, Call Wall, and Gamma Flip.

        Args:
            chain: List of option dicts with keys:
                   option_type, strike, gamma, open_interest,
                   contract_multiplier, implied_volatility, delta, vanna, charm
            spot: Current spot price

        Returns:
            Dict with net_gex (Millions), put_wall, call_wall, gamma_flip_level,
            gamma_flip (bool), per_strike_gex, etc.
        """
        if not chain or spot <= 0:
            return {
                "net_gex": 0.0,
                "put_wall": None,
                "call_wall": None,
                "gamma_flip_level": None,
                "gamma_flip": False,
                "per_strike_gex": [],
            }

        # Aggregate GEX by strike
        strike_gex: dict[float, dict[str, Any]] = {}

        for opt in chain:
            strike = opt.get("strike", 0)
            if strike <= 0:
                continue

            if strike not in strike_gex:
                strike_gex[strike] = {
                    "call_gex": 0.0, "put_gex": 0.0,
                    "tox_sum": 0.0, "bbo_sum": 0.0, "count": 0
                }

            gamma = opt.get("gamma", 0) or 0
            oi = opt.get("open_interest", 0) or 0
            multiplier = opt.get("contract_multiplier", 100) or 100
            opt_type = opt.get("option_type", opt.get("type", "")).upper()
            
            # Track flow metrics even if gamma/oi are zero (we still want depth info if available)
            strike_gex[strike]["tox_sum"] += opt.get("toxicity_score", 0.0)
            strike_gex[strike]["bbo_sum"] += opt.get("bbo_imbalance", 0.0)
            strike_gex[strike]["count"] += 1

            if gamma <= 0 or oi <= 0:
                # We do not compute GEX, but we already ensured the strike is in strike_gex
                continue

            # GEX formula: Gamma × OI × Spot² × Multiplier × 0.01
            gex = gamma * oi * (spot ** 2) * multiplier * 0.01

            if opt_type in ("CALL", "C"):
                strike_gex[strike]["call_gex"] += gex
            elif opt_type in ("PUT", "P"):
                strike_gex[strike]["put_gex"] -= gex  # Put GEX is negative

        if not strike_gex:
            return {
                "net_gex": 0.0,
                "put_wall": None,
                "call_wall": None,
                "gamma_flip_level": None,
                "gamma_flip": False,
                "per_strike_gex": [],
            }

        # Build per-strike GEX list
        per_strike = []
        total_call_gex = 0.0
        total_put_gex = 0.0
        max_call_gex = 0.0
        max_put_gex = 0.0
        call_wall_strike = None
        put_wall_strike = None

        for strike in sorted(strike_gex.keys()):
            data = strike_gex[strike]
            call_g = data["call_gex"]
            put_g = data["put_gex"]
            net_g = call_g + put_g
            cnt = data["count"]
            avg_tox = data["tox_sum"] / cnt if cnt > 0 else 0.0
            avg_bbo = data["bbo_sum"] / cnt if cnt > 0 else 0.0

            total_call_gex += call_g
            total_put_gex += put_g

            per_strike.append({
                "strike": strike,
                "call_gex": call_g,
                "put_gex": put_g,
                "net_gex": net_g,
                "toxicity_score": avg_tox,
                "bbo_imbalance": avg_bbo,
            })

            # Track walls (max absolute GEX)
            if call_g > max_call_gex:
                max_call_gex = call_g
                call_wall_strike = strike

            if abs(put_g) > max_put_gex:
                max_put_gex = abs(put_g)
                put_wall_strike = strike

        # Net GEX in Millions
        net_gex_dollars = total_call_gex + total_put_gex
        net_gex_millions = net_gex_dollars / 1_000_000.0

        # Gamma Flip detection (zero-crossing nearest to spot)
        gamma_flip_level = self._find_gamma_flip(per_strike, spot)
        gamma_flip = gamma_flip_level is not None

        return {
            "net_gex": net_gex_millions,
            "put_wall": put_wall_strike,
            "call_wall": call_wall_strike,
            "gamma_flip_level": gamma_flip_level,
            "gamma_flip": gamma_flip,
            "per_strike_gex": per_strike,
            "total_call_gex": total_call_gex / 1_000_000.0,
            "total_put_gex": total_put_gex / 1_000_000.0,
        }

    def _find_gamma_flip(
        self,
        per_strike: list[dict[str, Any]],
        spot: float,
    ) -> float | None:
        """Find the Gamma Flip level (zero-crossing of net GEX curve).

        Finds the zero-crossing closest to the current spot price
        using linear interpolation between adjacent strikes.
        """
        if len(per_strike) < 2:
            return None

        crossings: list[float] = []

        for i in range(len(per_strike) - 1):
            a = per_strike[i]
            b = per_strike[i + 1]
            net_a = a["net_gex"]
            net_b = b["net_gex"]

            # Check for sign change
            if (net_a > 0 and net_b < 0) or (net_a < 0 and net_b > 0):
                # Linear interpolation
                strike_a = a["strike"]
                strike_b = b["strike"]
                denom = net_a - net_b
                if abs(denom) > 1e-10:
                    flip = strike_a + (net_a / denom) * (strike_b - strike_a)
                    crossings.append(flip)

        if not crossings:
            return None

        # Return crossing closest to spot
        return min(crossings, key=lambda x: abs(x - spot))

    # =========================================================================
    # Gamma Profile (curve for visualization)
    # =========================================================================

    def compute_gamma_profile(
        self,
        chain: list[dict[str, Any]],
        spot: float,
        t_years: float | None = None,
    ) -> list[dict[str, float]]:
        """Compute gamma profile curve using DYNAMIC Greeks simulation.
        
        Refactor FIX: Instead of using current Gamma for all price points,
        we re-run BSM for every simulated spot price to capture non-linearities.
        """
        # We need BSM utils here since we're re-simulating
        from app.services.analysis.bsm import compute_greeks
        from app.config import settings

        range_pct = settings.gamma_profile_range_pct  # 10%
        steps = settings.gamma_profile_steps  # 50

        low = spot * (1 - range_pct)
        high = spot * (1 + range_pct)
        step_size = (high - low) / steps

        # Use current TTM if not provided
        if t_years is None:
            from app.services.analysis.bsm import get_trading_time_to_maturity
            from datetime import datetime
            from zoneinfo import ZoneInfo
            t_years = get_trading_time_to_maturity(datetime.now(ZoneInfo("US/Eastern")))

        profile = []
        for i in range(steps + 1):
            sim_spot = low + i * step_size
            sim_net_gex = 0.0

            for opt in chain:
                strike = opt.get("strike", 0)
                iv = opt.get("implied_volatility", 0)
                oi = opt.get("open_interest", 0)
                opt_type = opt.get("type", opt.get("option_type", "")).upper()
                multiplier = opt.get("contract_multiplier", 100)

                if iv <= 0 or oi <= 0 or strike <= 0:
                    continue

                # Re-calculate Gamma at sim_spot
                g = compute_greeks(
                    spot=sim_spot,
                    strike=strike,
                    iv=iv,
                    t_years=t_years,
                    opt_type=opt_type,
                    r=settings.risk_free_rate,
                    q=settings.bsm_dividend_yield,
                )
                
                # GEX_i = Gamma_i × OI_i × SimSpot² × Multiplier × 0.01
                gex = g["gamma"] * oi * (sim_spot ** 2) * multiplier * 0.01
                
                if opt_type in ("CALL", "C"):
                    sim_net_gex += gex
                else:
                    sim_net_gex -= gex

            profile.append({
                "price": round(sim_spot, 2),
                "net_gex": sim_net_gex / 1_000_000.0,
            })

        return profile

    # =========================================================================
    # Net Vanna Exposure
    # =========================================================================

    def compute_net_vanna(
        self,
        chain: list[dict[str, Any]],
        spot: float,
    ) -> float:
        """Compute Net Vanna exposure.

        Vanna = dDelta/dSigma
        Both calls and puts contribute with the same sign.
        Total Vanna = Sum(Vanna_i × OI_i)
        """
        total_vanna = 0.0

        for opt in chain:
            vanna = opt.get("vanna", 0) or 0
            oi = opt.get("open_interest", 0) or 0
            multiplier = opt.get("contract_multiplier", 100) or 100

            if oi <= 0:
                continue

            total_vanna += vanna * oi * multiplier

        return total_vanna

    # =========================================================================
    # Net Charm Exposure
    # =========================================================================

    def compute_net_charm(
        self,
        chain: list[dict[str, Any]],
    ) -> float:
        """Compute Net Charm (Delta Decay) exposure.

        Charm = dDelta/dTime
        Significant in 0DTE as it explodes in final hours.
        """
        total_charm = 0.0

        for opt in chain:
            charm = opt.get("charm", 0) or 0
            oi = opt.get("open_interest", 0) or 0
            multiplier = opt.get("contract_multiplier", 100) or 100

            if oi <= 0:
                continue

            total_charm += charm * oi * multiplier

        return total_charm

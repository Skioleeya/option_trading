"""BSM Greeks Engine — 0DTE Production Grade
 
Pure-Python, zero-dependency Black-Scholes-Merton implementation.
Includes:
  - Gamma Singularity Protection (10-min time floor)
  - Sticky-Strike IV Momentum Adjustment for cached-IV correction on spot jumps
"""

import math
from datetime import datetime
from zoneinfo import ZoneInfo


# ---------------------------------------------------------------------------
# Core Statistical Functions
# ---------------------------------------------------------------------------

def norm_cdf(x: float) -> float:
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)


# ---------------------------------------------------------------------------
# Time to Maturity
# ---------------------------------------------------------------------------

import logging

logger = logging.getLogger(__name__)

def get_trading_time_to_maturity(now: datetime) -> float:
    """Calculate TTM in 0DTE trading time (years).

    1 trading year = 252 days * 390 minutes = 98280 minutes.
    Market closes at 16:00 ET.

    NOTE: A 10-minute floor is enforced to prevent the ATM Gamma singularity
    (sqrt(t) → 0 causes Γ → ∞) from destabilising the system in the last
    minutes of the session.
    """
    tz = ZoneInfo("US/Eastern")
    # Make now timezone-aware if it isn't already
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    close_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
    minutes_remaining = (close_time - now).total_seconds() / 60.0

    MIN_MINUTES_FLOOR = 10.0          # ← Gamma singularity guard
    return max(MIN_MINUTES_FLOOR / 98280.0, minutes_remaining / 98280.0)


# ---------------------------------------------------------------------------
# Sticky-Strike IV Momentum Adjustment
# ---------------------------------------------------------------------------

def skew_adjust_iv(
    cached_iv: float,
    spot_now: float,
    spot_ref: float,
    opt_type: str,
    skew_sensitivity: float = 2.0,
) -> float:
    """Apply a Sticky-Strike momentum correction to a cached IV.

    When spot moves between IV-cache refreshes, the 0DTE skew surface
    shifts.  This function approximates that shift with an empirical rule:

        ΔIV ≈ -skew_sensitivity × (ΔS / S_ref)

    Economic intuition (well-established in dealer-flow literature):
    • Spot ↑  →  put IV falls, call IV rises  →  ΔIV < 0 for puts, > 0 for calls
    • Spot ↓  →  fear spike, put IV surges     →  ΔIV > 0 for puts, < 0 for calls
    The *sign* convention:
    - For CALLS  :  ΔIV = +skew_sensitivity × log_return   (positive correlation)
    - For PUTS   :  ΔIV = -skew_sensitivity × log_return   (negative/fear correlation)

    Args:
        cached_iv       : Raw IV from the last REST baseline (decimal, e.g. 0.20).
        spot_now        : Current spot (from WebSocket tick).
        spot_ref        : Spot at the time of the last IV sync.
        opt_type        : 'CALL' or 'PUT'.
        skew_sensitivity: Empirical multiplier. Default 2.0 is calibrated for SPY
                          0DTE intraday dynamics (≈ a 1% spot move → ±2% IV nudge).

    Returns:
        Adjusted IV (decimal), clamped to [0.01, 5.0] for safety.
    """
    if spot_ref <= 0 or spot_now <= 0:
        return cached_iv

    log_return = math.log(spot_now / spot_ref)     # ≈ ΔS/S for small moves

    is_call = opt_type.upper() in ("CALL", "C")

    if is_call:
        # Calls benefit from positive momentum (vol smile right-shift)
        delta_iv = skew_sensitivity * log_return
    else:
        # Puts spike on fear (inverse correlation)
        delta_iv = -skew_sensitivity * log_return

    adjusted_iv = cached_iv + delta_iv

    # Safety clamp: IV must stay in a physically meaningful range
    return max(0.01, min(5.0, adjusted_iv))


# ---------------------------------------------------------------------------
# Full BSM Greeks
# ---------------------------------------------------------------------------

def compute_greeks(
    spot: float,
    strike: float,
    iv: float,
    t_years: float,
    opt_type: str,
    r: float = 0.05,
    q: float = 0.0,
) -> dict[str, float]:
    """Calculate BSM Greeks with continuous dividend yield.

    Args:
        spot     : Underlying spot price.
        strike   : Option strike price.
        iv       : Implied volatility (decimal, e.g., 0.20 for 20%).
                   Should be the *adjusted* IV from skew_adjust_iv, not the
                   raw cached value.
        t_years  : Time to maturity in years (use get_trading_time_to_maturity).
        opt_type : 'CALL' or 'PUT'.
        r        : Annual risk-free rate (continuous compounding).
        q        : Annual dividend yield (continuous compounding).

    Returns:
        Dictionary with keys: delta, gamma, theta, vega, vanna, charm.
    """
    _zero = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "vanna": 0.0, "charm": 0.0}
    if iv <= 0 or spot <= 0 or strike <= 0 or t_years <= 0:
        return _zero

    sqrt_t = math.sqrt(t_years)
    d1 = (math.log(spot / strike) + (r - q + (iv ** 2) / 2.0) * t_years) / (iv * sqrt_t)
    d2 = d1 - iv * sqrt_t
    nd1 = norm_pdf(d1)
    eq_t = math.exp(-q * t_years)
    er_t = math.exp(-r * t_years)

    opt_type = opt_type.upper()
    is_call = opt_type in ("CALL", "C")

    if is_call:
        delta = eq_t * norm_cdf(d1)
        theta = (
            -(spot * iv * eq_t * nd1) / (2.0 * sqrt_t)
            - r * strike * er_t * norm_cdf(d2)
            + q * spot * eq_t * norm_cdf(d1)
        )
        charm = (
            q * eq_t * norm_cdf(d1)
            - eq_t * nd1 * (2.0 * (r - q) * t_years - d2 * iv * sqrt_t)
            / (2.0 * t_years * iv * sqrt_t)
        )
        rho = strike * t_years * er_t * norm_cdf(d2) * 0.01  # per 1% move
    else:
        delta = -eq_t * norm_cdf(-d1)
        theta = (
            -(spot * iv * eq_t * nd1) / (2.0 * sqrt_t)
            + r * strike * er_t * norm_cdf(-d2)
            - q * spot * eq_t * norm_cdf(-d1)
        )
        charm = (
            -q * eq_t * norm_cdf(-d1)
            - eq_t * nd1 * (2.0 * (r - q) * t_years - d2 * iv * sqrt_t)
            / (2.0 * t_years * iv * sqrt_t)
        )
        rho = -strike * t_years * er_t * norm_cdf(-d2) * 0.01  # per 1% move


    gamma = eq_t * nd1 / (spot * iv * sqrt_t)
    
    # Defensive Log: Catch Gamma singularity
    if t_years < 0.001 and gamma > 5.0:
        logger.debug(f"[L1 BSM] Near-Singularity Gamma detected: {gamma:.2f} for Strike {strike} (TTM: {t_years:.5f}y, Spot: {spot:.2f})")
        
    vega  = spot * eq_t * nd1 * sqrt_t * 0.01      # per 1pp IV move
    vanna = -eq_t * nd1 * d2 / iv                  # ∂Δ/∂σ (unnormalised)

    return {
        "delta":  delta,
        "gamma":  gamma,
        "theta":  theta / 365.0,    # annualised → daily
        "vega":   vega,
        "vanna":  vanna * 0.01,     # normalised to 1pp
        "charm":  charm / 365.0,    # annualised → daily
        "rho":    rho
    }

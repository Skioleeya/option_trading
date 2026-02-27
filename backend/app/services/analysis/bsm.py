import math
from datetime import datetime

def norm_cdf(x: float) -> float:
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)

def get_trading_time_to_maturity(now: datetime) -> float:
    """Calculate TTM in 0DTE trading time (years).
    1 trading year = 252 days * 390 minutes = 98280 minutes
    Market closes at 16:00 ET.
    """
    close_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
    minutes_remaining = (close_time - now).total_seconds() / 60.0
    return max(1e-6, minutes_remaining / 98280.0)

def compute_greeks(
    spot: float,
    strike: float,
    iv: float,
    t_years: float,
    opt_type: str,
    r: float = 0.05,
    q: float = 0.0,
) -> dict[str, float]:
    """Calculate BSM Greeks for 0DTE options.
    
    Args:
        spot: Underlying spot price.
        strike: Option strike price.
        iv: Implied volatility (decimal, e.g., 0.20 for 20%).
        t_years: Time to maturity in years.
        opt_type: 'CALL' or 'PUT'.
    """
    if iv <= 0 or spot <= 0 or strike <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "vanna": 0.0, "charm": 0.0}

    d1 = (math.log(spot / strike) + (r - q + (iv**2) / 2.0) * t_years) / (iv * math.sqrt(t_years))
    d2 = d1 - iv * math.sqrt(t_years)
    nd1 = norm_pdf(d1)
    
    opt_type = opt_type.upper()
    is_call = opt_type in ("CALL", "C")
    
    if is_call:
        delta = math.exp(-q * t_years) * norm_cdf(d1)
        theta = (- (spot * iv * math.exp(-q * t_years) * nd1) / (2 * math.sqrt(t_years))
                 - r * strike * math.exp(-r * t_years) * norm_cdf(d2)
                 + q * spot * math.exp(-q * t_years) * norm_cdf(d1))
        charm = q * math.exp(-q * t_years) * norm_cdf(d1) - math.exp(-q * t_years) * nd1 * (2*(r-q)*t_years - d2*iv*math.sqrt(t_years)) / (2*t_years*iv*math.sqrt(t_years))
    else:
        delta = -math.exp(-q * t_years) * norm_cdf(-d1)
        theta = (- (spot * iv * math.exp(-q * t_years) * nd1) / (2 * math.sqrt(t_years))
                 + r * strike * math.exp(-r * t_years) * norm_cdf(-d2)
                 - q * spot * math.exp(-q * t_years) * norm_cdf(-d1))
        charm = -q * math.exp(-q * t_years) * norm_cdf(-d1) - math.exp(-q * t_years) * nd1 * (2*(r-q)*t_years - d2*iv*math.sqrt(t_years)) / (2*t_years*iv*math.sqrt(t_years))
        
    gamma = math.exp(-q * t_years) * nd1 / (spot * iv * math.sqrt(t_years))
    vega = spot * math.exp(-q * t_years) * nd1 * math.sqrt(t_years) * 0.01

    vanna = -math.exp(-q * t_years) * nd1 * d2 / iv

    return {
        "delta": delta,
        "gamma": gamma,
        "theta": theta / 365.0,
        "vega": vega,
        "vanna": vanna * 0.01,
        "charm": charm / 365.0
    }

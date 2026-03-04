"""Market structure analysis thresholds: HV, CHARM, SKEW, Gamma Profile."""

from pydantic import Field

from app.config._base import BaseConfig


class MarketStructureConfig(BaseConfig):
    """HV regimes, CHARM decay, SKEW dynamics, and Gamma Profile parameters."""

    # Historical Volatility Thresholds
    hv_low_threshold: float = Field(
        default=12.0, description="HV level below which volatility regime is LOW (percent)"
    )
    hv_normal_threshold: float = Field(
        default=20.0, description="HV level below which volatility regime is NORMAL (percent)"
    )
    hv_elevated_threshold: float = Field(
        default=30.0, description="HV level below which volatility regime is ELEVATED (percent)"
    )
    hv_crisis_threshold: float = Field(
        default=35.0, description="HV level above which triggers CRISIS alert (percent)"
    )
    hv_history_size: int = Field(
        default=100, description="Number of HV data points to keep for percentile calculation"
    )

    # CHARM (Delta Decay) — 0DTE focused
    charm_accel_threshold: float = Field(
        default=2.5,
        description="CHARM threshold for ACCEL_DECAY state (|CHARM| > 2.5, limits intraday noise)",
    )
    charm_terminal_threshold: float = Field(
        default=60.0,
        description="CHARM threshold for TERMINAL DECAY (High-speed 0DTE dealer hedging zone)",
    )

    # SKEW Dynamics (25-Delta normalized)
    skew_speculative_max: float = Field(
        default=0.08, description="Skew < 0.08 = Call demand spike (SPECULATIVE/Fomo)"
    )
    skew_defensive_min: float = Field(
        default=0.22, description="Skew > 0.22 = Put hedging spike (DEFENSIVE/Fear)"
    )

    # Gamma Flip
    gamma_flip_ttl_ticks: int = Field(
        default=300, description="Ticks to hold gamma flip level after detection lost"
    )

    # Gamma Profile
    gamma_profile_range_pct: float = Field(
        default=0.10, description="Price range (+/-) for gamma profile curve (10%)"
    )
    gamma_profile_steps: int = Field(
        default=50, description="Number of points to calculate on gamma profile curve"
    )

    # Mark Price Validation
    mark_min_price: float = Field(
        default=0.10, description="Minimum mark price to consider valid"
    )
    mark_max_spread_pct: float = Field(
        default=0.10, description="Maximum bid-ask spread percentage (10%)"
    )

    # Market Trading Hours (US Eastern Time)
    market_open_hour: int = Field(default=9, description="Market open hour (ET)")
    market_open_minute: int = Field(default=30, description="Market open minute (ET)")
    market_close_hour: int = Field(default=16, description="Market close hour (ET)")
    market_close_minute: int = Field(default=0, description="Market close minute (ET)")

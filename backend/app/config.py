"""
Configuration management for SPY 0DTE Dashboard Backend.

Handles environment variables and provides timezone conversion utilities.
All timestamps are standardized to US/Eastern market time.
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ============================================================================
# GLOBAL TIMEZONE CONSTANT
# ============================================================================
TIMEZONE = "US/Eastern"
"""Global timezone for all market data display. US stock market operates in Eastern Time."""


# ============================================================================
# TIMEZONE CONVERSION UTILITY
# ============================================================================
def convert_to_market_time(utc_dt: datetime) -> datetime:
    """
    Convert UTC datetime to US/Eastern market time.

    This function handles the conversion from UTC timestamps (as provided by
    Longport API) to US/Eastern timezone (where US stock markets operate).

    The conversion automatically accounts for:
    - EST (Eastern Standard Time, UTC-5) during winter
    - EDT (Eastern Daylight Time, UTC-4) during summer

    Args:
        utc_dt: A datetime object in UTC timezone. Can be either:
                - Naive datetime (assumed to be UTC)
                - Aware datetime with UTC timezone info

    Returns:
        datetime: Timezone-aware datetime in US/Eastern timezone
    """
    # Create timezone objects
    utc_tz = ZoneInfo("UTC")
    eastern_tz = ZoneInfo(TIMEZONE)

    # If the datetime is naive (no timezone info), assume it's UTC
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=utc_tz)

    # Convert to US/Eastern timezone
    eastern_dt = utc_dt.astimezone(eastern_tz)

    return eastern_dt


# ============================================================================
# APPLICATION SETTINGS
# ============================================================================
class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.

    Uses pydantic-settings v2 to automatically load variables from:
    1. Environment variables (highest priority)
    2. .env file in the current working directory (typically `backend/.env`)
    3. ../.env (repo root) for local development convenience
    4. Default values (fallback)
    """

    # Longport API credentials
    longport_app_key: str = Field(..., description="Longport OpenAPI App Key")
    longport_app_secret: str = Field(..., description="Longport OpenAPI App Secret")
    longport_access_token: str = Field(..., description="Longport OpenAPI Access Token")

    # Application settings
    log_level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    # WebSocket settings
    websocket_update_interval: int = Field(
        default=3, description="Interval in seconds for WebSocket dashboard updates"
    )

    # Decay chart settings
    decay_stale_seconds: int = Field(
        default=60,
        description="Mark Opening ATM decay legs stale when quotes haven't updated within this many seconds",
    )

    # Persistence (Redis + cold storage)
    redis_url: str | None = Field(
        default=None,
        description="Redis connection URL for persistence (e.g. redis://:pass@127.0.0.1:6380/0)",
    )

    opening_atm_cold_storage_root: str = Field(
        default=str(Path(__file__).resolve().parents[1] / "data" / "opening_atm"),
        description="Cold storage root directory for Opening ATM data",
    )

    opening_atm_redis_ttl_seconds: int = Field(
        default=172800,
        description="TTL (seconds) for Opening ATM Redis keys (baseline + stream)",
    )

    opening_atm_stream_maxlen: int = Field(
        default=30000,
        description="Approx max length for Opening ATM Redis stream",
    )

    # Wall Migration Persistence (v1.0)
    wall_migration_cold_storage_root: str = Field(
        default=str(Path(__file__).resolve().parents[1] / "data" / "wall_migration"),
        description="Cold storage root directory for Wall Migration data",
    )

    wall_migration_redis_ttl_seconds: int = Field(
        default=172800,
        description="TTL (seconds) for Wall Migration Redis keys",
    )

    wall_migration_stream_maxlen: int = Field(
        default=10000,
        description="Approx max length for Wall Migration Redis stream",
    )

    # Agent A (Trend) Configuration
    # Uses VWAP (Anchored VWAP) exclusively

    # VWAP Settings (Anchored VWAP)
    agent_a_vwap_std_band_1: float = Field(
        default=1.0, description="VWAP Standard Deviation Band 1 (sigma multiplier for normal range)"
    )
    agent_a_vwap_std_band_2: float = Field(
        default=2.0, description="VWAP Standard Deviation Band 2 (sigma multiplier for extreme range)"
    )
    agent_a_vwap_slope_window: int = Field(
        default=60, description="VWAP slope calculation window (seconds)"
    )
    agent_a_vwap_slope_threshold: float = Field(
        default=0.05, description="VWAP slope threshold for trend bias (price change per second)"
    )

    # Agent B (Structure) Configuration
    agent_b_th_spot_entry: float = Field(
        default=0.15, description="Spot RoC entry threshold (Abs %, 0.15=0.15%)"
    )
    agent_b_th_spot_exit: float = Field(default=0.06, description="Spot RoC exit threshold (Abs %) - raised from 0.03% to avoid noise exits")
    agent_b_th_opt_fade: float = Field(default=-5.0, description="Option RoC fade threshold (pp)")
    agent_b_th_opt_recover: float = Field(
        default=3.0, description="Option RoC recover threshold (pp)"
    )
    agent_b_k_entry: int = Field(default=2, description="Consecutive hits for entry")
    agent_b_k_exit: int = Field(default=2, description="Consecutive hits for exit")
    agent_b_th_opt_rocket_pct: float = Field(default=8.0, description="Rocket exit threshold (%) - lowered from 15% for practical trigger")
    agent_b_gf_cooldown: int = Field(default=12, description="Gamma Flip cooldown ticks")

    # Agent B1 v2.0 Microstructure Analysis Feature Flag
    agent_b1_v2_enabled: bool = Field(
        default=True,
        description="Enable Agent B1 v2.0 microstructure analysis (IV velocity, wall migration, vanna flow)",
    )

    # Architecture v3.0 Feature Flag
    use_v3_architecture: bool = Field(
        default=False,
        description="Use new v3.0 layered architecture (Infrastructure/Domain/Application/Presentation). If False, uses legacy agents.",
    )

    # Agent B Timing (v5.3) - Critical for 1Hz updates
    agent_b_gamma_tick_interval: float = Field(
        default=0.5, description="Minimum seconds between Agent B runs"
    )
    agent_b_min_window_span: float = Field(
        default=0.8, description="Min seconds for T vs T-2 RoC calc"
    )
    agent_b_max_window_span: float = Field(
        default=5.0, description="Max seconds for T vs T-2 RoC calc"
    )

    # Agent G (Decision) Configuration
    agent_g_wall_magnet_pct: float = Field(
        default=0.3, description="Distance % to consider 'Approaching' a Wall"
    )
    agent_g_wall_breakout_pct: float = Field(
        default=0.1, description="Distance % beyond Wall to consider 'Breach'"
    )

    # SPY IV Volatility Thresholds (using ATM Call IV %)
    # Regimes: LOW (<12%), NORMAL (12-20%), ELEVATED (20-30%), HIGH (30-35%), EXTREME (>35%)
    iv_low_max: float = Field(
        default=12.0, description="IV < this = LOW regime (crushed vol, Long Gamma)"
    )
    iv_normal_max: float = Field(
        default=20.0, description="IV < this = NORMAL regime (typical, Neutral strategies)"
    )
    iv_elevated_max: float = Field(
        default=30.0, description="IV < this = ELEVATED regime (fear, Short Vol)"
    )
    iv_high_max: float = Field(
        default=35.0, description="IV < this = HIGH regime (volatility decay zone, 30-35%)"
    )
    # IV >= iv_high_max = EXTREME regime (crisis, FADE/Cash, >35%)

    # Variance Risk Premium (VRP = IV - HV) thresholds
    vrp_cheap_threshold: float = Field(
        default=-2.0, description="VRP < this = Options CHEAP (IV < HV)"
    )
    vrp_expensive_threshold: float = Field(
        default=5.0, description="VRP > this = Options EXPENSIVE (IV >> HV)"
    )
    vrp_trap_threshold: float = Field(
        default=10.0, description="VRP > this = THETA TRAP (extreme premium, DANGER)"
    )

    # ============================================================================
    # CENTRALIZED GEX THRESHOLDS (ALL IN MILLIONS - NO HARDCODING ALLOWED)
    # ============================================================================
    # New Regime Classification Thresholds (2026-02-07):
    # - SUPER_PIN:   |GEX| >= 1000M
    # - DAMPING:     200M <= |GEX| < 500M (positive GEX only)
    # - NEUTRAL:     |GEX| < 200M
    # - ACCELERATION: net_gex < 0 (any negative value)
    # ============================================================================
    gex_neutral_threshold: float = Field(
        default=200, description="|GEX| < 200M = NEUTRAL regime"
    )
    gex_damping_threshold: float = Field(
        default=200, description="200M <= |GEX| = DAMPING regime entry (positive GEX)"
    )
    gex_extreme_threshold: float = Field(
        default=500, description="|GEX| upper bound for DAMPING regime (< 500M)"
    )
    gex_super_pin_threshold: float = Field(
        default=1000, description="|GEX| >= 1000M = SUPER_PIN regime"
    )
    gex_strong_negative: float = Field(
        default=-500, description="GEX <= -500M = strong NEGATIVE_ACCELERATION"
    )
    gex_strong_positive: float = Field(
        default=500, description="GEX >= 500M = strong POSITIVE_DAMPING"
    )
    gex_acceleration_threshold: float = Field(
        default=0, description="net_gex < 0 = ACCELERATION regime (any negative)"
    )
    # Legacy field name (kept for backward compatibility)
    gex_moderate_threshold: float = Field(
        default=200, description="|GEX| >= 200M = MODERATE intensity (legacy)"
    )

    # Agent G Dynamic Weight Engine Configuration
    agent_g_iv_weight: float = Field(
        default=0.25, description="IV Velocity base weight"
    )
    agent_g_wall_weight: float = Field(
        default=0.30, description="Wall Dynamics base weight"
    )
    agent_g_vanna_weight: float = Field(
        default=0.20, description="Vanna Flow base weight"
    )
    agent_g_mtf_weight: float = Field(
        default=0.25, description="Multi-Timeframe Consensus base weight"
    )

    # Wall Migration Tracker Configuration
    wall_snapshot_interval_seconds: float = Field(
        default=900, description="Wall snapshot interval (900 = 15 minutes)"
    )
    wall_displacement_threshold: float = Field(
        default=1.0, description="Strike points to consider wall 'moved'"
    )
    volume_reinforcement_threshold: int = Field(
        default=500, description="Contracts for 'significant volume' reinforcement"
    )

    # MTF Consensus Weights (must sum to 1.0)
    # v3.0 FIX: 0DTE-optimized weights (1M+5M=70% can override stale 15M signal)
    mtf_weight_1min: float = Field(
        default=0.35, description="1min timeframe weight for MTF consensus (entry trigger)"
    )
    mtf_weight_5min: float = Field(
        default=0.35, description="5min timeframe weight for MTF consensus (core rhythm)"
    )
    mtf_weight_15min: float = Field(
        default=0.30, description="15min timeframe weight for MTF consensus (trend background)"
    )

    # MTF Window Seconds for IV/Vanna trackers
    mtf_window_seconds_1min: int = Field(
        default=120, description="IV tracker window for 1min timeframe (Increased to 120s for Exhaustion sync)"
    )
    mtf_window_seconds_5min: int = Field(
        default=300, description="IV tracker window for 5min timeframe"
    )
    mtf_window_seconds_15min: int = Field(
        default=900, description="IV tracker window for 15min timeframe"
    )

    # IV Velocity Thresholds
    iv_roc_threshold_pct: float = Field(
        default=2.0, description="IV change threshold (pp) to classify as significant"
    )
    spot_roc_threshold_pct: float = Field(
        default=0.03, description="Spot move threshold (%) for divergence detection"
    )

    # Vanna Flow Thresholds
    vanna_danger_zone_threshold: float = Field(
        default=0.5, description="Spot-Vol correlation threshold for DANGER_ZONE"
    )
    vanna_grind_stable_threshold: float = Field(
        default=-0.8, description="Inverse correlation threshold for GRIND_STABLE"
    )

    # Historical Volatility Thresholds (for Volatility Regime classification)
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

    # CHARM (Delta Decay) Thresholds
    charm_accel_threshold: float = Field(
        default=1.0, description="CHARM threshold for ACCEL_DECAY state (|CHARM| > 1.0)"
    )
    charm_terminal_threshold: float = Field(
        default=50.0, description="CHARM threshold for TERMINAL DECAY alert (CHARM > 50)"
    )

    # Historical Volatility Tracker Configuration
    hv_history_size: int = Field(
        default=100, description="Number of HV data points to keep for percentile calculation"
    )

    # Gamma Flip TTL (ticks to hold flip level after lost)
    gamma_flip_ttl_ticks: int = Field(
        default=300, description="Ticks to hold gamma flip level after detection lost"
    )

    # Mark Price Validation Thresholds
    mark_min_price: float = Field(
        default=0.10, description="Minimum mark price to consider valid"
    )
    mark_max_spread_pct: float = Field(
        default=0.10, description="Maximum bid-ask spread percentage (10%)"
    )

    # Gamma Profile Calculation Parameters
    gamma_profile_range_pct: float = Field(
        default=0.10, description="Price range (+/-) for gamma profile curve (10%)"
    )
    gamma_profile_steps: int = Field(
        default=50, description="Number of points to calculate on gamma profile curve"
    )

    # Market Trading Hours (US Eastern Time)
    market_open_hour: int = Field(
        default=9, description="Market open hour (ET)"
    )
    market_open_minute: int = Field(
        default=30, description="Market open minute (ET)"
    )
    market_close_hour: int = Field(
        default=16, description="Market close hour (ET)"
    )
    market_close_minute: int = Field(
        default=0, description="Market close minute (ET)"
    )

    # Trading Session Restrictions
    agent_b_burn_in_minutes: int = Field(
        default=15, description="Burn-in period after open (minutes)"
    )
    agent_b_near_close_minutes: int = Field(
        default=5, description="No-entry period before close (minutes)"
    )

    # FastAPI settings
    api_host: str = Field(default="0.0.0.0", description="Host to bind the API server")
    api_port: int = Field(default=8001, description="Port to bind the API server")

    # CORS settings
    cors_origins: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins",
    )

    # ============================================================================
    # DECOUPLING CONSTANTS
    # ============================================================================

    # AgentG Decision Fusion threshold
    fusion_confidence_threshold: float = Field(
        default=0.75,
        description=(
            "Minimum fused-signal confidence for Fusion Engine to override Trend logic "
            "(AgentG.decide). Values in [0, 1]."
        ),
    )

    # Put-Call Parity implied-spot settings
    risk_free_rate: float = Field(
        default=0.05,
        description="Annual risk-free rate used for Put-Call Parity implied spot calculation",
    )
    implied_spot_pcp_strikes: int = Field(
        default=10,
        description="Number of ATM-region strikes used in PCP implied-spot calculation",
    )

    # WebSocket allowed origins
    ws_allowed_origins: str = Field(
        default=(
            "http://localhost:5173,http://localhost:3000,"
            "http://127.0.0.1:5173,http://127.0.0.1:3000"
        ),
        description="Comma-separated WebSocket allowed origins for WS handshake validation",
    )

    # Broadcaster cache freshness
    broadcaster_cache_freshness_seconds: float = Field(
        default=2.0,
        description=(
            "AgentGRunner payload reuse window (seconds). "
            "Should be less than websocket_update_interval."
        ),
    )

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================
settings = Settings()
"""Global settings instance. Import this to access configuration throughout the app."""

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
    websocket_update_interval: float = Field(
        default=1.0, description="Interval in seconds for backend computation loop (data fetch + agents)"
    )
    ws_broadcast_interval: float = Field(
        default=1.0, description="Interval in seconds for WebSocket broadcast to frontend clients"
    )

    # Decay chart settings
    decay_stale_seconds: int = Field(
        default=60,
        description="Mark Opening ATM decay legs stale when quotes haven't updated within this many seconds",
    )

    # Strike Window Settings (Phase 32)
    strike_window_size: float = Field(
        default=15.0,
        description="Active window (+/- points) around spot to fetch option quotes",
    )
    research_window_size: float = Field(
        default=70.0,
        description="Wide window (+/- points) for liquidity research scans",
    )

    # Persistence (Redis + cold storage)
    redis_host: str = Field(default="127.0.0.1", description="Redis host")
    redis_port: int = Field(default=6380, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database index")
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
    # Post-2022 research (e.g. JF, RFS) indicates structural VRP compression in 0DTE era.
    vrp_baseline_hv: float = Field(
        default=13.5,
        description=(
            "PP-1 FIX: VRP 计算所用的历史波动率基线 (annualized %). "
            "默认 13.5 = SPY 结构性 HV。可通过环境变量 VRP_BASELINE_HV 覆盖。"
        ),
    )
    vrp_cheap_threshold: float = Field(
        default=-1.5, description="VRP < this = Options CHEAP (Vol sellers underpricing risk)"
    )
    vrp_expensive_threshold: float = Field(
        default=3.5, description="VRP > this = Options EXPENSIVE (Requires strict hedging)"
    )
    vrp_trap_threshold: float = Field(
        default=7.0, description="VRP > this = THETA TRAP (Extreme premium, strict mean-reversion expected)"
    )
    vrp_veto_threshold: float = Field(
        default=8.0,
        description=(
            "Phase 25A — VRP Veto Gate (Paper: Muravyev et al. SSRN #4019647). "
            "When VRP > this value, all LONG_CALL/PUT signals are vetoed as NO_TRADE. "
            "Entry into expensive options has negative expected value (EV < 0). "
            "Default 8.0 = 2× the TRAP threshold, i.e. extreme rare event only."
        )
    )
    vrp_bargain_boost: float = Field(
        default=1.15,
        description=(
            "Phase 25A — Confidence multiplier applied when VRP is in BARGAIN territory. "
            "Signals are more reliable when options are cheap (IV underpricing). "
            "Default 1.15 = +15% confidence boost."
        )
    )

    # Jump Detection & Safety Valve (Phase 27)
    jump_z_threshold: float = Field(
        default=3.0,
        description="Phase 27.1 — Z-Score threshold for price jump detection (|Z| > threshold)."
    )
    jump_lockout_seconds: int = Field(
        default=60,
        description="Phase 27.3 — Duration of signal halt after a jump is detected."
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

    # GEX Acceleration Boost (PP-4 Fix — originally hardcoded in agent_g.py)
    gex_accel_threshold: float = Field(
        default=-500.0,
        description=(
            "PP-4 FIX: net_gex < 此值时激活加速置信度增益 (原硬编码 -500M). "
            "可通过环境变量 GEX_ACCEL_THRESHOLD 覆盖。"
        ),
    )
    gex_accel_boost_bearish: float = Field(
        default=1.20,
        description=(
            "PP-4 FIX: 负 Gamma 环境下 BEARISH 信号的置信度增益倍数 (原硬编码 1.20)。"
        ),
    )
    gex_accel_boost_bullish: float = Field(
        default=1.15,
        description=(
            "PP-4 FIX: 负 Gamma 环境下 BULLISH 信号的置信度增益倍数 (原硬编码 1.15)。"
        ),
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
    agent_g_vib_weight: float = Field(
        default=0.20,
        description=(
            "PP-2/PP-6 FIX: Volume Imbalance 分量基础权重 (原硬编码 0.20)。"
            "可通过环境变量 AGENT_G_VIB_WEIGHT 覆盖。"
        ),
    )

    # Phase 3 — L2 Micro Flow Signal Component
    # Academic reference: OFI Papers 2022-2024 (see MicroFlow_Research_2022_2026.md)
    agent_g_micro_flow_weight: float = Field(
        default=0.12,
        description=(
            "Phase 3: L2 Micro Flow (toxicity + bbo_imbalance) 分量基础权重。"
            "比 MTF/VIB 低，避免单因子过拟合 (Paper 4: OFI alpha 衰减快)。"
        ),
    )
    micro_flow_toxicity_threshold: float = Field(
        default=0.25,
        description=(
            "Phase 3: micro_flow 方向信号触发门限。"
            "|micro_score| < 0.25 时视为噪音不产生方向信号。"
            "(Paper 4+5 依据: 绝对值< 0.2 不显著，加 0.05 缓冲)"
        ),
    )


    # MTF Alignment Hysteresis & EWMA Smoothing (PP-2 Fix)
    mtf_alignment_damp_entry: float = Field(
        default=0.34,
        description=(
            "PP-2 FIX: MTF alignment 低于此值时激活置信度阻尼 (原硬编码 0.34)。"
        ),
    )
    mtf_alignment_damp_exit: float = Field(
        default=0.38,
        description=(
            "PP-2 FIX: MTF alignment 高于此值时退出置信度阻尼 (原硬编码 0.38)。"
        ),
    )
    mtf_alignment_ewma_alpha: float = Field(
        default=0.30,
        description=(
            "PP-2 FIX: MTF alignment EWMA 平滑因子。"
            "0.0 = 纯历史（无响应），1.0 = 瞬时值（无平滑）。"
            "默认 0.30 消除单 tick 离散跳跃。"
        ),
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

    # Vanna Flow Thresholds (S-VOL Correlation)
    # Dealer hedging dynamics shift significantly when correlation flips positive.
    vanna_danger_zone_threshold: float = Field(
        default=0.45, description="Spot-Vol correlation > 0.45 (Positive correlation warns of directional break/bubble)"
    )
    vanna_grind_stable_threshold: float = Field(
        default=-0.75, description="Inverse correlation < -0.75 (Healthy stable market regime)"
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

    # CHARM (Delta Decay) Thresholds - 0DTE Focused
    # 0DTE theta decay accelerates 100x vs 45DTE, especially around 2PM ET ("Dealer O'Clock").
    charm_accel_threshold: float = Field(
        default=2.5, description="CHARM threshold for ACCEL_DECAY state (|CHARM| > 2.5, limits intraday noise)"
    )
    charm_terminal_threshold: float = Field(
        default=60.0, description="CHARM threshold for TERMINAL DECAY (High-speed 0DTE dealer hedging zone)"
    )

    # SKEW DYNAMICS Thresholds (25-Delta normalized)
    # Ratio: (Put25d_IV - Call25d_IV) / ATM_IV
    skew_speculative_max: float = Field(
        default=0.08, description="Skew < 0.08 = Call demand spike (SPECULATIVE/Fomo)"
    )
    skew_defensive_min: float = Field(
        default=0.22, description="Skew > 0.22 = Put hedging spike (DEFENSIVE/Fear)"
    )

    # ============================================================================
    # DEG-FLOW COMPOSITE SYSTEM (Phases D+E+G)
    # ============================================================================
    # Base weights (must sum to 1.0 within each set)
    flow_weight_d: float = Field(default=0.40, description="FlowEngine_D base weight (Gamma Imbalance)")
    flow_weight_e: float = Field(default=0.35, description="FlowEngine_E base weight (Vanna × ΔIV)")
    flow_weight_g: float = Field(default=0.25, description="FlowEngine_G base weight (OI Momentum)")

    # Charm Surge weights (last 2 hours of 0DTE session)
    flow_charm_surge_weight_d: float = Field(default=0.50, description="D weight during Charm Surge zone")
    flow_charm_surge_weight_e: float = Field(default=0.30, description="E weight during Charm Surge zone")
    flow_charm_surge_weight_g: float = Field(default=0.20, description="G weight during Charm Surge zone")

    # NEUTRAL GEX zone weights
    flow_neutral_gex_weight_d: float = Field(default=0.30, description="D weight in NEUTRAL GEX zone")
    flow_neutral_gex_weight_e: float = Field(default=0.40, description="E weight in NEUTRAL GEX zone")
    flow_neutral_gex_weight_g: float = Field(default=0.30, description="G weight in NEUTRAL GEX zone")

    # Z-Score intensity thresholds
    flow_zscore_extreme_threshold: float = Field(default=3.0, description="|z_deg| >= this → EXTREME intensity")
    flow_intensity_high_threshold: float = Field(default=1.5, description="|z_deg| >= this → HIGH intensity")

    # OI cache TTL (seconds)
    flow_oi_cache_ttl_seconds: int = Field(default=86400, description="TTL for OI Redis snapshots (one trading day)")

    # Minimum volume for a contract to appear in Active Options
    flow_active_min_volume: int = Field(default=100, description="Minimum volume threshold for Active Options inclusion")

    # ============================================================================
    # VPIN (Volume-synchronized Probability of Informed Trading) — Practice 2
    # ============================================================================
    # Academic: Easley, Lopez de Prado & O'Hara (2012) — VPIN uses volume buckets
    # rather than clock time, which is critical for 0DTE high-burst environments.
    vpin_bucket_size: float = Field(
        default=500.0,
        description=(
            "Practice 2: Volume bucket size for VPIN dynamic alpha calculation. "
            "Toxicity score updates significantly only when this volume is accumulated per bucket. "
            "Low-volume ticks (noise) get near-zero alpha; high-burst ticks get alpha≈1. "
            "Default 500 contracts represents a meaningful institutional-size print."
        ),
    )

    # ============================================================================
    # Volume Acceleration Squeeze Detection — Practice 3
    # ============================================================================
    # Academic: Muravyev & Pearson (2024/2026) — Volume accel divergence from GEX
    # distribution signals Dealer delta-hedge exhaustion (Dealer Squeeze).
    vol_accel_squeeze_threshold: float = Field(
        default=3.0,
        description=(
            "Practice 3: Vol Accel Ratio threshold for Dealer Squeeze alert. "
            "If current-1s volume / 60s-average-volume exceeds this AND net_gex < 0, "
            "a squeeze condition is flagged and AgentG confidence is boosted. "
            "Default 3.0 = 1s volume is 3× its 60s average (burst signal)."
        ),
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

    # ============================================================================
    # GREEKS 2.0 & QUOTA MANAGEMENT
    # ============================================================================
    bsm_dividend_yield: float = Field(
        default=0.0,
        description="Annual dividend yield used for BSM Greeks calculation (SPY ≈ 0.0)",
    )
    bsm_year_trading_minutes: int = Field(
        default=98280,
        description="Total trading minutes in a year (252 days * 390 minutes)",
    )
    cooling_buffer_quota: int = Field(
        default=90,
        description="Number of symbol-request slots per minute to keep empty for window sliding",
    )
    iv_baseline_sync_interval: int = Field(
        default=300,
        description="Interval in seconds to refresh the full chain's baseline via REST (Fallback only)",
    )
    max_total_quota_per_min: int = Field(
        default=500,
        description="Hard limit of symbol-requests per rolling minute for LongPort API",
    )
    subscription_max: int = Field(
        default=480,
        description="Maximum concurrent WebSocket subscriptions allowed (reserved for Core+Wide)",
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

"""[P1] DEG Flow Engine, VPIN, Volume Acceleration, and OI cache configuration."""

from pydantic import Field

from app.config._base import BaseConfig


class FlowEngineConfig(BaseConfig):
    """DEG composite flow engine, VPIN toxicity, and volume acceleration squeeze detection."""

    # ── DEG-FLOW Base Weights ─────────────────────────────────────────────────
    flow_weight_d: float = Field(
        default=0.40, description="FlowEngine_D base weight (Gamma Imbalance)"
    )
    flow_weight_e: float = Field(
        default=0.35, description="FlowEngine_E base weight (Vanna × ΔIV)"
    )
    flow_weight_g: float = Field(
        default=0.25, description="FlowEngine_G base weight (OI Momentum)"
    )

    # Charm Surge weights (last 2 hours of 0DTE session)
    flow_charm_surge_weight_d: float = Field(
        default=0.50, description="D weight during Charm Surge zone"
    )
    flow_charm_surge_weight_e: float = Field(
        default=0.30, description="E weight during Charm Surge zone"
    )
    flow_charm_surge_weight_g: float = Field(
        default=0.20, description="G weight during Charm Surge zone"
    )

    # NEUTRAL GEX zone weights
    flow_neutral_gex_weight_d: float = Field(
        default=0.30, description="D weight in NEUTRAL GEX zone"
    )
    flow_neutral_gex_weight_e: float = Field(
        default=0.40, description="E weight in NEUTRAL GEX zone"
    )
    flow_neutral_gex_weight_g: float = Field(
        default=0.30, description="G weight in NEUTRAL GEX zone"
    )

    # Z-Score intensity thresholds
    flow_zscore_extreme_threshold: float = Field(
        default=3.0, description="|z_deg| >= this → EXTREME intensity"
    )
    flow_intensity_high_threshold: float = Field(
        default=1.5, description="|z_deg| >= this → HIGH intensity"
    )

    # OI cache
    flow_oi_cache_ttl_seconds: int = Field(
        default=86400, description="TTL for OI Redis snapshots (one trading day)"
    )
    flow_active_min_volume: int = Field(
        default=100, description="Minimum volume threshold for Active Options inclusion"
    )

    # ── VPIN (Practice 2) ─────────────────────────────────────────────────────
    vpin_bucket_size: float = Field(
        default=500.0,
        description=(
            "Practice 2: Volume bucket size for VPIN dynamic alpha calculation. "
            "Low-volume ticks get near-zero alpha; high-burst ticks get alpha≈1. "
            "Default 500 contracts = meaningful institutional-size print."
        ),
    )

    # ── Volume Acceleration Squeeze (Practice 3) ──────────────────────────────
    vol_accel_squeeze_threshold: float = Field(
        default=3.0,
        description=(
            "Practice 3: Vol Accel Ratio threshold for Dealer Squeeze alert. "
            "If 1s vol / 60s-avg-vol exceeds this AND net_gex < 0 → squeeze flagged. "
            "Default 3.0 = 1s volume is 3× the 60s average."
        ),
    )

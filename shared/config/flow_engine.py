from pydantic import Field
from shared.config._base import BaseConfig

class FlowEngineConfig(BaseConfig):
    # VPIN / Order Flow
    vpin_bucket_size: float = Field(default=50000)
    flow_active_min_volume: int = Field(default=100)
    research_window_size: int = Field(default=120)

    # DEG Composer Weights
    flow_charm_surge_weight_d: float = Field(default=0.4)
    flow_charm_surge_weight_e: float = Field(default=0.3)
    flow_charm_surge_weight_g: float = Field(default=0.3)
    
    flow_neutral_gex_weight_d: float = Field(default=0.33)
    flow_neutral_gex_weight_e: float = Field(default=0.33)
    flow_neutral_gex_weight_g: float = Field(default=0.34)
    
    flow_weight_d: float = Field(default=0.4)
    flow_weight_e: float = Field(default=0.3)
    flow_weight_g: float = Field(default=0.3)

    # Intensity Thresholds
    flow_zscore_extreme_threshold: float = Field(default=2.5)
    flow_intensity_high_threshold: float = Field(default=1.5)

    # Institutional Upgrade (v4.0)
    flow_sweep_multiplier: float = Field(default=1.25)
    flow_sweep_z_threshold: float = Field(default=1.5)
    flow_market_depth_baseline: float = Field(default=1000.0)  # Reference USD depth

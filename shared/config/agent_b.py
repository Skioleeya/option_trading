from pydantic import Field
from shared.config._base import BaseConfig

class AgentBConfig(BaseConfig):
    # Agent B1 Feature Flags
    agent_b1_v2_enabled: bool = Field(default=True)
    
    # Trap Machine Thresholds
    agent_b_gamma_tick_interval: float = Field(default=1.0)
    agent_b_th_spot_entry: float = Field(default=0.15)
    agent_b_th_spot_exit: float = Field(default=0.05)
    agent_b_th_opt_fade: float = Field(default=-2.0)
    agent_b_th_opt_recover: float = Field(default=1.0)
    agent_b_k_entry: int = Field(default=2)
    agent_b_k_exit: int = Field(default=2)
    agent_b_th_opt_rocket_pct: float = Field(default=15.0)
    agent_b_min_window_span: float = Field(default=2.0)
    agent_b_max_window_span: float = Field(default=15.0)

    # MTF Weights
    mtf_weight_1min: float = Field(default=0.5)
    mtf_weight_5min: float = Field(default=0.3)
    mtf_weight_15min: float = Field(default=0.2)

    # Skew Thresholds
    skew_speculative_max: float = Field(default=-0.10)
    skew_defensive_min: float = Field(default=0.15)

    # Practice 3: Squeeze Threshold
    vol_accel_squeeze_threshold: float = Field(default=2.5)

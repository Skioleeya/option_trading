from pydantic import Field
from shared.config._base import BaseConfig

class AgentGConfig(BaseConfig):
    # Agent G Weights
    agent_g_iv_weight: float = Field(default=0.25)
    agent_g_wall_weight: float = Field(default=0.20)
    agent_g_vanna_weight: float = Field(default=0.15)
    agent_g_mtf_weight: float = Field(default=0.20)
    agent_g_vib_weight: float = Field(default=0.20)
    agent_g_micro_flow_weight: float = Field(default=0.10)
    agent_g_wall_magnet_pct: float = Field(default=0.01)
    agent_g_wall_breakout_pct: float = Field(default=0.005)
    fusion_confidence_threshold: float = Field(default=0.5)

    # GEX Thresholds (In Millions, matching 2026 100B+ normative scale)
    gex_neutral_threshold: float = Field(default=20000.0)      # 20B
    gex_super_pin_threshold: float = Field(default=100000.0)   # 100B
    gex_strong_positive: float = Field(default=50000.0)        # 50B
    gex_strong_negative: float = Field(default=-50000.0)       # -50B
    gex_moderate_threshold: float = Field(default=30000.0)     # 30B
    gex_accel_threshold: float = Field(default=10000.0)        # 10B

    # VRP Thresholds
    vrp_baseline_hv: float = Field(default=0.15)
    vrp_trap_threshold: float = Field(default=10.0)
    vrp_expensive_threshold: float = Field(default=5.0)
    vrp_cheap_threshold: float = Field(default=-5.0)
    vrp_veto_threshold: float = Field(default=-2.0)
    vrp_bargain_boost: float = Field(default=1.2)

    # MTF Alignment
    mtf_alignment_ewma_alpha: float = Field(default=0.1)
    mtf_alignment_damp_entry: float = Field(default=0.34)
    mtf_alignment_damp_exit: float = Field(default=0.38)

    # Micro Flow
    micro_flow_toxicity_threshold: float = Field(default=0.25)
    
    # Agent Sync
    agent_b_gamma_tick_interval: float = Field(default=1.0)

    # MTF Windows (Missing from reconstruction)
    mtf_window_seconds_1min: int = Field(default=60)
    mtf_window_seconds_5min: int = Field(default=300)
    mtf_window_seconds_15min: int = Field(default=900)

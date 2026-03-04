from pydantic import Field
from shared.config._base import BaseConfig

class MarketStructureConfig(BaseConfig):
    # Wall Migration
    wall_snapshot_interval_seconds: int = Field(default=300)
    wall_displacement_threshold: float = Field(default=0.01)
    volume_reinforcement_threshold: float = Field(default=1000)

    # Vanna Flow
    vanna_danger_zone_threshold: float = Field(default=0.8)
    vanna_grind_stable_threshold: float = Field(default=0.2)

    # Intraday ROC
    spot_roc_threshold_pct: float = Field(default=0.0003)
    iv_roc_threshold_pct: float = Field(default=2.0)

    # Gamma Profile
    gamma_profile_range_pct: float = Field(default=0.1)
    gamma_profile_steps: int = Field(default=50)

    # Charm
    charm_terminal_threshold: float = Field(default=0.5)

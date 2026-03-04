from pydantic import Field
from shared.config._base import BaseConfig

class AgentAConfig(BaseConfig):
    # VWAP Bands
    agent_a_vwap_std_band_1: float = Field(default=1.0)
    agent_a_vwap_std_band_2: float = Field(default=2.0)
    
    # VWAP Slope
    agent_a_vwap_slope_window: int = Field(default=60)
    agent_a_vwap_slope_threshold: float = Field(default=0.0001)

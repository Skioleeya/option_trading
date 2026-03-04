"""Agent A (Trend / VWAP) configuration."""

from pydantic import Field

from app.config._base import BaseConfig


class AgentAConfig(BaseConfig):
    """VWAP-based trend agent configuration (Anchored VWAP)."""

    agent_a_vwap_std_band_1: float = Field(
        default=1.0,
        description="VWAP Standard Deviation Band 1 (sigma multiplier for normal range)",
    )
    agent_a_vwap_std_band_2: float = Field(
        default=2.0,
        description="VWAP Standard Deviation Band 2 (sigma multiplier for extreme range)",
    )
    agent_a_vwap_slope_window: int = Field(
        default=60, description="VWAP slope calculation window (seconds)"
    )
    agent_a_vwap_slope_threshold: float = Field(
        default=0.05,
        description="VWAP slope threshold for trend bias (price change per second)",
    )

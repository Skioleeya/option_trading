"""Agent B (Structure / Microstructure) configuration."""

from pydantic import Field

from shared.config._base import BaseConfig


class AgentBConfig(BaseConfig):
    """Structure agent (RoC / gamma / timing) configuration."""

    # Rate-of-Change entry/exit
    agent_b_th_spot_entry: float = Field(
        default=0.15, description="Spot RoC entry threshold (Abs %, 0.15=0.15%)"
    )
    agent_b_th_spot_exit: float = Field(
        default=0.06,
        description="Spot RoC exit threshold (Abs %) - raised from 0.03% to avoid noise exits",
    )
    agent_b_th_opt_fade: float = Field(
        default=-5.0, description="Option RoC fade threshold (pp)"
    )
    agent_b_th_opt_recover: float = Field(
        default=3.0, description="Option RoC recover threshold (pp)"
    )
    agent_b_k_entry: int = Field(default=2, description="Consecutive hits for entry")
    agent_b_k_exit: int = Field(default=2, description="Consecutive hits for exit")
    agent_b_th_opt_rocket_pct: float = Field(
        default=8.0,
        description="Rocket exit threshold (%) - lowered from 15% for practical trigger",
    )
    agent_b_gf_cooldown: int = Field(
        default=12, description="Gamma Flip cooldown ticks"
    )

    # Feature flags
    agent_b1_v2_enabled: bool = Field(
        default=True,
        description="Enable Agent B1 v2.0 microstructure analysis (IV velocity, wall migration, vanna flow)",
    )
    use_v3_architecture: bool = Field(
        default=False,
        description="Use new v3.0 layered architecture. If False, uses legacy agents.",
    )

    # Timing (v5.3)
    agent_b_gamma_tick_interval: float = Field(
        default=0.5, description="Minimum seconds between Agent B runs"
    )
    agent_b_min_window_span: float = Field(
        default=0.8, description="Min seconds for T vs T-2 RoC calc"
    )
    agent_b_max_window_span: float = Field(
        default=5.0, description="Max seconds for T vs T-2 RoC calc"
    )

    # Trading session restrictions
    agent_b_burn_in_minutes: int = Field(
        default=15, description="Burn-in period after open (minutes)"
    )
    agent_b_near_close_minutes: int = Field(
        default=5, description="No-entry period before close (minutes)"
    )

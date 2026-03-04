"""[P0] LongPort API credentials and top-level system parameters."""

from pydantic import Field

from shared.config._base import BaseConfig


class APICredentialsConfig(BaseConfig):
    """LongPort OpenAPI credentials and core system settings."""

    # LongPort API credentials
    longport_app_key: str = Field(..., description="Longport OpenAPI App Key")
    longport_app_secret: str = Field(..., description="Longport OpenAPI App Secret")
    longport_access_token: str = Field(..., description="Longport OpenAPI Access Token")

    # Logging
    log_level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
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

    # Decay chart settings
    decay_stale_seconds: int = Field(
        default=60,
        description="Mark Opening ATM decay legs stale when quotes haven't updated within this many seconds",
    )

    # Tier Polling Selection (Requested: Disable Tier 2 and Tier 3)
    enable_tier2_polling: bool = Field(
        default=False,
        description="Enable Tier 2 (2DTE) REST polling",
    )
    enable_tier3_polling: bool = Field(
        default=False,
        description="Enable Tier 3 (Weekly) REST polling",
    )
    # LongPort API Rate Limits (User-defined per 2026-03-03 policy)
    longport_api_rate_limit: float = Field(
        default=8.0,
        description="Global rate limit (requests/sec) for LongPort OpenAPI REST calls",
    )
    longport_api_burst: int = Field(
        default=10,
        description="Burst token capacity (max concurrent requests) for LongPort OpenAPI REST calls",
    )
    longport_api_max_concurrent: int = Field(
        default=5,
        description="Max concurrent HTTP requests (hard connection cap) to LongPort",
    )

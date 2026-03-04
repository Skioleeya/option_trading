"""FastAPI server, CORS, BSM Greeks, and API quota configuration."""

from pydantic import Field

from app.config._base import BaseConfig


class ServerConfig(BaseConfig):
    """FastAPI host/port, CORS, BSM model parameters, and LongPort quota management."""

    # FastAPI
    api_host: str = Field(default="0.0.0.0", description="Host to bind the API server")
    api_port: int = Field(default=8001, description="Port to bind the API server")

    # CORS
    cors_origins: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins",
    )

    # BSM Greeks 2.0
    bsm_dividend_yield: float = Field(
        default=0.0,
        description="Annual dividend yield used for BSM Greeks calculation (SPY ≈ 0.0)",
    )
    bsm_year_trading_minutes: int = Field(
        default=98280,
        description="Total trading minutes in a year (252 days * 390 minutes)",
    )

    # LongPort quota management
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

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

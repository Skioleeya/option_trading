"""[P1] Redis and cold-storage persistence configuration."""

from pathlib import Path

from pydantic import Field

from shared.config._base import BaseConfig


class PersistenceConfig(BaseConfig):
    """Redis connection and cold-storage settings for ATM / Wall Migration data."""

    # Redis connection
    redis_host: str = Field(default="127.0.0.1", description="Redis host")
    redis_port: int = Field(default=6380, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database index")
    redis_url: str | None = Field(
        default=None,
        description="Redis connection URL for persistence (e.g. redis://:pass@127.0.0.1:6380/0)",
    )

    # Opening ATM
    opening_atm_cold_storage_root: str = Field(
        default=str(Path(__file__).resolve().parents[2] / "data" / "opening_atm"),
        description="Cold storage root directory for Opening ATM data",
    )
    opening_atm_redis_ttl_seconds: int = Field(
        default=172800,
        description="TTL (seconds) for Opening ATM Redis keys (baseline + stream)",
    )
    opening_atm_stream_maxlen: int = Field(
        default=30000,
        description="Approx max length for Opening ATM Redis stream",
    )

    # Wall Migration
    wall_migration_cold_storage_root: str = Field(
        default=str(Path(__file__).resolve().parents[2] / "data" / "wall_migration"),
        description="Cold storage root directory for Wall Migration data",
    )
    wall_migration_redis_ttl_seconds: int = Field(
        default=172800,
        description="TTL (seconds) for Wall Migration Redis keys",
    )
    wall_migration_stream_maxlen: int = Field(
        default=10000,
        description="Approx max length for Wall Migration Redis stream",
    )

    # History query controls
    history_default_view: str = Field(default="compact", description="Default /history view")
    history_schema_default: str = Field(
        default="v2",
        description="Default history schema version (v1|v2)",
    )
    history_max_fields_per_query: int = Field(
        default=64,
        description="Maximum projected fields allowed per query",
    )
    history_max_points_per_query: int = Field(
        default=5000,
        description="Maximum points allowed per inline history query",
    )
    history_v2_enabled: bool = Field(
        default=True,
        description="Enable schema=v2 columnar JSON history responses",
    )

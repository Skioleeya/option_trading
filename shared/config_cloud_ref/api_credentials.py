"""[P0] LongPort API credentials and top-level system parameters."""

from pydantic import AliasChoices, Field

from shared.config._base import BaseConfig


class APICredentialsConfig(BaseConfig):
    """LongPort OpenAPI credentials and core system settings."""

    # LongPort / Longbridge API credentials (dual env alias for compatibility)
    longport_app_key: str = Field(
        ...,
        description="Longport OpenAPI App Key",
        validation_alias=AliasChoices("LONGPORT_APP_KEY", "LONGBRIDGE_APP_KEY"),
    )
    longport_app_secret: str = Field(
        ...,
        description="Longport OpenAPI App Secret",
        validation_alias=AliasChoices("LONGPORT_APP_SECRET", "LONGBRIDGE_APP_SECRET"),
    )
    longport_access_token: str = Field(
        ...,
        description="Longport OpenAPI Access Token",
        validation_alias=AliasChoices("LONGPORT_ACCESS_TOKEN", "LONGBRIDGE_ACCESS_TOKEN"),
    )
    longport_http_url: str = Field(
        default="https://openapi.longportapp.com",
        description="HTTP endpoint url (official default from Longport Rust SDK Config::from_env)",
        validation_alias=AliasChoices("LONGPORT_HTTP_URL", "LONGBRIDGE_HTTP_URL"),
    )
    longport_quote_ws_url: str = Field(
        default="wss://openapi-quote.longportapp.com/v2",
        description="Quote websocket endpoint url (official default from Longport Rust SDK Config::from_env)",
        validation_alias=AliasChoices("LONGPORT_QUOTE_WS_URL", "LONGBRIDGE_QUOTE_WS_URL"),
    )
    longport_trade_ws_url: str = Field(
        default="wss://openapi-trade.longportapp.com/v2",
        description="Trade websocket endpoint url (official default from Longport Rust SDK Config::from_env)",
        validation_alias=AliasChoices("LONGPORT_TRADE_WS_URL", "LONGBRIDGE_TRADE_WS_URL"),
    )
    longport_language: str = Field(
        default="en",
        description="Language identifier (en/zh-CN/zh-HK)",
        validation_alias=AliasChoices("LONGPORT_LANGUAGE", "LONGBRIDGE_LANGUAGE"),
    )
    longport_enable_overnight: bool = Field(
        default=False,
        description="Enable overnight quote mode",
        validation_alias=AliasChoices("LONGPORT_ENABLE_OVERNIGHT", "LONGBRIDGE_ENABLE_OVERNIGHT"),
    )
    longport_startup_strict_connectivity: bool = Field(
        default=True,
        description="Fail fast on startup when quote REST probe cannot reach any endpoint profile",
        validation_alias=AliasChoices(
            "LONGPORT_STARTUP_STRICT_CONNECTIVITY",
            "LONGBRIDGE_STARTUP_STRICT_CONNECTIVITY",
        ),
    )

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

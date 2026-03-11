from pydantic import AliasChoices, Field
from shared.config._base import BaseConfig

class APICredentialsConfig(BaseConfig):
    # LongPort / Longbridge credentials (dual env alias for compatibility)
    longport_app_key: str = Field(
        ...,
        validation_alias=AliasChoices("LONGPORT_APP_KEY", "LONGBRIDGE_APP_KEY"),
    )
    longport_app_secret: str = Field(
        ...,
        validation_alias=AliasChoices("LONGPORT_APP_SECRET", "LONGBRIDGE_APP_SECRET"),
    )
    longport_access_token: str = Field(
        ...,
        validation_alias=AliasChoices("LONGPORT_ACCESS_TOKEN", "LONGBRIDGE_ACCESS_TOKEN"),
    )

    # Official Longport Rust SDK gateway defaults (from Config::from_env docs)
    longport_http_url: str = Field(
        default="https://openapi.longportapp.com",
        validation_alias=AliasChoices("LONGPORT_HTTP_URL", "LONGBRIDGE_HTTP_URL"),
    )
    longport_quote_ws_url: str = Field(
        default="wss://openapi-quote.longportapp.com/v2",
        validation_alias=AliasChoices("LONGPORT_QUOTE_WS_URL", "LONGBRIDGE_QUOTE_WS_URL"),
    )
    longport_trade_ws_url: str = Field(
        default="wss://openapi-trade.longportapp.com/v2",
        validation_alias=AliasChoices("LONGPORT_TRADE_WS_URL", "LONGBRIDGE_TRADE_WS_URL"),
    )
    longport_language: str = Field(
        default="en",
        validation_alias=AliasChoices("LONGPORT_LANGUAGE", "LONGBRIDGE_LANGUAGE"),
    )
    longport_enable_overnight: bool = Field(
        default=False,
        validation_alias=AliasChoices("LONGPORT_ENABLE_OVERNIGHT", "LONGBRIDGE_ENABLE_OVERNIGHT"),
    )
    longport_startup_strict_connectivity: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "LONGPORT_STARTUP_STRICT_CONNECTIVITY",
            "LONGBRIDGE_STARTUP_STRICT_CONNECTIVITY",
        ),
    )

    # Longport API Flow Control (Hard Limits: 10 calls/s, 5 concurrent, 500 subs)
    longport_api_rate_limit: float = Field(default=10.0)       # Official cap: <=10 req/s
    longport_api_burst: int = Field(default=10)
    longport_api_max_concurrent: int = Field(default=5)        # Official cap: <=5 in-flight
    longport_symbol_rate_per_min: float = Field(default=240.0) # Conservative symbol budget for option metadata APIs
    longport_symbol_burst: int = Field(default=50)             # Small startup burst to avoid minute quota spikes

    # System Control
    log_level: str = Field(default="INFO")
    enable_tier2_polling: bool = Field(default=True)
    enable_tier3_polling: bool = Field(default=True)
    subscription_max: int = Field(default=500)                 # Hard-clamped to official cap(500) at runtime
    longport_runtime_mode: str = Field(default="rust_only")    # rust_only | python_fallback

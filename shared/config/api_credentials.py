from pydantic import AliasChoices, Field
from shared.config._base import BaseConfig
from shared_rust.contracts import (
    DEFAULT_L0_BATCH_INTERVAL_MS,
    DEFAULT_L0_BATCH_MAX_ROWS,
    DEFAULT_L0_IPC_SHM_BYTES,
    DEFAULT_LONGPORT_CONNECT_RETRIES,
    DEFAULT_LONGPORT_CONNECT_RETRY_BASE_SEC,
    L0_BATCH_INTERVAL_ENV_KEY,
    L0_BATCH_MAX_ROWS_ENV_KEY,
    L0_IPC_SHM_BYTES_ENV_KEY,
    L0_IPC_SIGNAL_ENV_KEY,
)

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
    longport_connect_retries: int = Field(
        default=DEFAULT_LONGPORT_CONNECT_RETRIES,
        validation_alias=AliasChoices("LONGPORT_CONNECT_RETRIES"),
    )
    longport_connect_retry_base_sec: float = Field(
        default=DEFAULT_LONGPORT_CONNECT_RETRY_BASE_SEC,
        validation_alias=AliasChoices("LONGPORT_CONNECT_RETRY_BASE_SEC"),
    )
    l0_ipc_signal_name: str = Field(
        default="",
        validation_alias=AliasChoices(L0_IPC_SIGNAL_ENV_KEY),
    )
    l0_batch_interval_ms: int = Field(
        default=DEFAULT_L0_BATCH_INTERVAL_MS,
        validation_alias=AliasChoices(L0_BATCH_INTERVAL_ENV_KEY),
    )
    l0_batch_max_rows: int = Field(
        default=DEFAULT_L0_BATCH_MAX_ROWS,
        validation_alias=AliasChoices(L0_BATCH_MAX_ROWS_ENV_KEY),
    )
    l0_ipc_shm_bytes: int = Field(
        default=DEFAULT_L0_IPC_SHM_BYTES,
        validation_alias=AliasChoices(L0_IPC_SHM_BYTES_ENV_KEY),
    )

    # Longport API Flow Control (Hard Limits: 10 calls/s, 5 concurrent, 500 subs)
    longport_api_rate_limit: float = Field(default=10.0)       # Official cap: <=10 req/s
    longport_api_burst: int = Field(default=10)
    longport_api_max_concurrent: int = Field(default=5)        # Official cap: <=5 in-flight
    longport_symbol_rate_per_min: float = Field(default=240.0) # Conservative symbol budget for option metadata APIs
    longport_symbol_burst: int = Field(default=50)             # Small startup burst to avoid minute quota spikes
    longport_startup_symbol_rate_per_min: float = Field(default=180.0)
    longport_startup_symbol_burst: int = Field(default=20)
    longport_steady_symbol_rate_per_min: float = Field(default=240.0)
    longport_steady_symbol_burst: int = Field(default=50)
    longport_metadata_weight: int = Field(default=5)
    longport_metadata_ttl_sec: int = Field(default=30)
    longport_warmup_merge_window_sec: int = Field(default=20)
    longport_research_startup_stable_sec: int = Field(default=120)
    longport_subscription_ready_timeout_sec: int = Field(default=60)

    # System Control
    log_level: str = Field(default="INFO")
    enable_tier2_polling: bool = Field(default=True)
    enable_tier3_polling: bool = Field(default=True)
    subscription_max: int = Field(default=500)                 # Hard-clamped to official cap(500) at runtime
    subscription_initial_strike_steps_per_side: int = Field(default=30)
    subscription_dynamic_lock_after_sec: int = Field(default=600)
    subscription_volume_coverage: float = Field(default=0.90)
    subscription_core_buffer_steps: int = Field(default=5)
    subscription_rebalance_confirmations: int = Field(default=2)
    subscription_rebalance_min_shift_steps: int = Field(default=2)
    subscription_rebalance_interval_sec: int = Field(default=60)

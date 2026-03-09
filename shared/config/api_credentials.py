from pydantic import Field
from shared.config._base import BaseConfig

class APICredentialsConfig(BaseConfig):
    # Longport Credentials
    longport_app_key: str = Field(..., env="LONGPORT_APP_KEY")
    longport_app_secret: str = Field(..., env="LONGPORT_APP_SECRET")
    longport_access_token: str = Field(..., env="LONGPORT_ACCESS_TOKEN")

    # Longport API Flow Control (Hard Limits: 10 calls/s, 5 concurrent, 500 subs)
    longport_api_rate_limit: float = Field(default=9.0)        # Max 10/s, leaving 1.0 margin
    longport_api_burst: int = Field(default=10)
    longport_api_max_concurrent: int = Field(default=4)        # Max 5, leaving 1 margin
    longport_symbol_rate_per_min: float = Field(default=240.0) # Conservative symbol budget for option metadata APIs
    longport_symbol_burst: int = Field(default=50)             # Small startup burst to avoid minute quota spikes

    # System Control
    log_level: str = Field(default="INFO")
    enable_tier2_polling: bool = Field(default=True)
    enable_tier3_polling: bool = Field(default=True)
    subscription_max: int = Field(default=500)                 # Hard-clamped to official cap(500) at runtime
    longport_runtime_mode: str = Field(default="rust_only")    # rust_only | python_fallback

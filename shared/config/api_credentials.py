from pydantic import Field
from shared.config._base import BaseConfig

class APICredentialsConfig(BaseConfig):
    # Longport Credentials
    longport_app_key: str = Field(..., env="LONGPORT_APP_KEY")
    longport_app_secret: str = Field(..., env="LONGPORT_APP_SECRET")
    longport_access_token: str = Field(..., env="LONGPORT_ACCESS_TOKEN")

    # API Flow Control
    longport_api_rate_limit: float = Field(default=8.0)
    longport_api_burst: int = Field(default=10)
    longport_api_max_concurrent: int = Field(default=5)

    # System Control
    log_level: str = Field(default="INFO")
    enable_tier2_polling: bool = Field(default=True)
    enable_tier3_polling: bool = Field(default=True)
    subscription_max: int = Field(default=1000)

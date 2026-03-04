from pydantic import Field
from shared.config._base import BaseConfig

class ServerConfig(BaseConfig):
    # FastAPI Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8001)
    
    # BSM / Greeks Parameters
    risk_free_rate: float = Field(default=0.045)  # 4.5%
    bsm_dividend_yield: float = Field(default=0.015) # 1.5%

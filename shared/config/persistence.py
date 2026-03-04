from pydantic import Field
from shared.config._base import BaseConfig

class PersistenceConfig(BaseConfig):
    redis_host: str = Field(default="127.0.0.1")
    redis_port: int = Field(default=6380)
    
    opening_atm_redis_ttl_seconds: int = Field(default=86400 * 3) # 3 days
    opening_atm_cold_storage_root: str = Field(default="./data/atm_decay")

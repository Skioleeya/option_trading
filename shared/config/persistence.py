from pydantic import Field
from shared.config._base import BaseConfig

class PersistenceConfig(BaseConfig):
    redis_host: str = Field(default="127.0.0.1")
    redis_port: int = Field(default=6380)
    redis_db: int = Field(default=0)
    
    opening_atm_redis_ttl_seconds: int = Field(default=86400 * 3) # 3 days
    opening_atm_cold_storage_root: str = Field(default="./data/atm_decay")
    wall_migration_cold_storage_root: str = Field(default="./data/wall_migration")
    mtf_iv_cold_storage_root: str = Field(default="./data/mtf_iv")
    research_store_root: str = Field(default="./data/research")
    research_raw_retention_days: int = Field(default=7)
    research_feature_retention_days: int = Field(default=90)
    research_label_retention_days: int = Field(default=365)
    history_default_view: str = Field(default="compact")
    history_schema_default: str = Field(default="v2")
    history_max_fields_per_query: int = Field(default=64)
    history_max_points_per_query: int = Field(default=5000)
    history_v2_enabled: bool = Field(default=True)

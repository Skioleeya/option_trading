from pydantic import Field
from shared.config._base import BaseConfig

class AgentAConfig(BaseConfig):
    vwap_window_size: int = Field(default=300)

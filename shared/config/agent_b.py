from pydantic import Field
from shared.config._base import BaseConfig

class AgentBConfig(BaseConfig):
    roc_window_seconds: int = Field(default=60)

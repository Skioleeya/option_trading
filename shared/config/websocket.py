from pydantic import Field
from shared.config._base import BaseConfig
from typing import List

class WebSocketConfig(BaseConfig):
    ws_broadcast_interval: float = Field(default=1.0)
    websocket_update_interval: float = Field(default=1.0)
    cors_origins_list: List[str] = Field(default=["*"])

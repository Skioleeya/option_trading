from shared.config.api_credentials import APICredentialsConfig
from shared.config.websocket import WebSocketConfig
from shared.config.persistence import PersistenceConfig
from shared.config.agent_a import AgentAConfig
from shared.config.agent_b import AgentBConfig
from shared.config.agent_g import AgentGConfig
from shared.config.market_structure import MarketStructureConfig
from shared.config.flow_engine import FlowEngineConfig
from shared.config.server import ServerConfig

class Settings(
    APICredentialsConfig,
    WebSocketConfig,
    PersistenceConfig,
    AgentAConfig,
    AgentBConfig,
    AgentGConfig,
    MarketStructureConfig,
    FlowEngineConfig,
    ServerConfig,
):
    """Composed settings — inherits all domain configs via MRO."""
    pass

import pytz
from datetime import datetime

def convert_to_market_time(dt: datetime) -> datetime:
    """Convert UTC to US/Eastern market time."""
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(pytz.timezone('US/Eastern')).replace(tzinfo=None)

# Global singleton
settings = Settings()

__all__ = ["settings", "Settings", "convert_to_market_time"]

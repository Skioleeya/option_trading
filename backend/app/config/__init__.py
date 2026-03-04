"""
Configuration package for SPY 0DTE Dashboard Backend.

This package replaces the monolithic ``app/config.py`` with a set of
domain-scoped configuration fragments composed via Python multiple inheritance.

**Backward-Compatibility Guarantee:**
All existing imports continue to work unchanged::

    from app.config import settings          # ✅
    from app.config import TIMEZONE          # ✅
    from app.config import convert_to_market_time  # ✅

**New — Granular domain imports (no credentials required):**

    from app.config.agent_g import AgentGConfig   # for unit-testing AgentG
    from app.config.flow_engine import FlowEngineConfig

Domain modules
--------------
- ``_base``          — shared SettingsConfigDict
- ``api_credentials`` — LongPort API keys + system params  [P0]
- ``websocket``      — WS broadcast / allowed-origins
- ``persistence``    — Redis + cold-storage
- ``agent_a``        — VWAP trend agent
- ``agent_b``        — Structure / microstructure agent
- ``agent_g``        — Decision / fusion agent             [P0]
- ``market_structure`` — HV, CHARM, SKEW, Gamma Profile
- ``flow_engine``    — DEG / VPIN / Vol Accel              [P1]
- ``server``         — FastAPI, CORS, BSM, quota           [P1]
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config.api_credentials import APICredentialsConfig
from app.config.websocket import WebSocketConfig
from app.config.persistence import PersistenceConfig
from app.config.agent_a import AgentAConfig
from app.config.agent_b import AgentBConfig
from app.config.agent_g import AgentGConfig
from app.config.market_structure import MarketStructureConfig
from app.config.flow_engine import FlowEngineConfig
from app.config.server import ServerConfig


# ============================================================================
# GLOBAL TIMEZONE CONSTANT  (preserved from original config.py)
# ============================================================================
TIMEZONE = "US/Eastern"
"""Global timezone for all market data display. US stock market operates in Eastern Time."""


# ============================================================================
# TIMEZONE CONVERSION UTILITY  (preserved from original config.py)
# ============================================================================
def convert_to_market_time(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to US/Eastern market time.

    Handles EST (UTC-5) and EDT (UTC-4) automatically.

    Args:
        utc_dt: A datetime object in UTC timezone (naive or aware).

    Returns:
        datetime: Timezone-aware datetime in US/Eastern timezone.
    """
    utc_tz = ZoneInfo("UTC")
    eastern_tz = ZoneInfo(TIMEZONE)
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=utc_tz)
    return utc_dt.astimezone(eastern_tz)


# ============================================================================
# COMPOSED SETTINGS CLASS
# ============================================================================
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
    """Composed application settings.

    Inherits all domain config fragments via Python MRO.
    All fields are visible as a flat namespace (``settings.gex_neutral_threshold``,
    ``settings.redis_host``, etc.) exactly as before.
    """
    pass


# ============================================================================
# SINGLETON INSTANCE  (preserved public name)
# ============================================================================
settings = Settings()
"""Global settings instance. Import this to access configuration throughout the app."""


__all__ = [
    "settings",
    "Settings",
    "TIMEZONE",
    "convert_to_market_time",
    # Domain classes (for selective import in tests)
    "APICredentialsConfig",
    "WebSocketConfig",
    "PersistenceConfig",
    "AgentAConfig",
    "AgentBConfig",
    "AgentGConfig",
    "MarketStructureConfig",
    "FlowEngineConfig",
    "ServerConfig",
]

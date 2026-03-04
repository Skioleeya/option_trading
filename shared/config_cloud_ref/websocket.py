"""WebSocket broadcast and connection settings."""

from pydantic import Field

from shared.config._base import BaseConfig


class WebSocketConfig(BaseConfig):
    """WebSocket broadcast timing and allowed-origins configuration."""

    websocket_update_interval: float = Field(
        default=1.0,
        description="Interval in seconds for backend computation loop (data fetch + agents)",
    )
    ws_broadcast_interval: float = Field(
        default=1.0,
        description="Interval in seconds for WebSocket broadcast to frontend clients",
    )
    ws_allowed_origins: str = Field(
        default=(
            "http://localhost:5173,http://localhost:3000,"
            "http://127.0.0.1:5173,http://127.0.0.1:3000"
        ),
        description="Comma-separated WebSocket allowed origins for WS handshake validation",
    )
    broadcaster_cache_freshness_seconds: float = Field(
        default=2.0,
        description=(
            "AgentGRunner payload reuse window (seconds). "
            "Should be less than websocket_update_interval."
        ),
    )

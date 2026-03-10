from pydantic import Field
from shared.config._base import BaseConfig
from typing import List

class WebSocketConfig(BaseConfig):
    ws_broadcast_interval: float = Field(default=1.0)
    websocket_update_interval: float = Field(default=1.0)
    # Snapshot-version vs ATM-IV drift probe (app/loops/compute_loop.py)
    snapshot_iv_probe_epsilon: float = Field(default=1e-6)
    snapshot_iv_probe_confirm_ticks: int = Field(default=3)
    snapshot_iv_probe_activate_lag_seconds: float = Field(default=90.0)
    snapshot_iv_probe_ongoing_log_interval_seconds: float = Field(default=30.0)
    cors_origins_list: List[str] = Field(default=["*"])

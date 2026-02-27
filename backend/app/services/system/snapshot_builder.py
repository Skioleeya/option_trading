"""Unified Snapshot Builder.

Centralizes the assembly of Agent results, Data Feed snapshots,
and UI Presenter transformations into a single broadcast payload.
"""

import logging
import time
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from app.ui.micro_stats.presenter import MicroStatsPresenter
from app.ui.wall_migration.presenter import WallMigrationPresenter
from app.ui.depth_profile.presenter import DepthProfilePresenter

logger = logging.getLogger(__name__)

class SnapshotBuilder:
    """Assembles the final WebSocket payload for the frontend."""

    @staticmethod
    def build(
        snapshot: dict[str, Any],
        agent_result: Any,
        atm_decay_payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Convert raw agent outputs into a structured UI payload."""
        now = datetime.now(ZoneInfo("US/Eastern"))
        spot = snapshot.get("spot")

        # Extract agent data
        agent_data = agent_result.model_dump() if agent_result else None
        
        if not agent_data or "data" not in agent_data:
            return {
                "type": "dashboard_update",
                "timestamp": now.isoformat(),
                "spot": spot,
                "agent_g": agent_data,
            }

        # 1. Extract raw business state
        b_data = agent_data["data"].get("agent_b", {}).get("data", {})
        micro = b_data.get("micro_structure", {}).get("micro_structure_state", {})
        gex_regime = agent_data["data"].get("gex_regime", "NEUTRAL")
        vanna_state = micro.get("vanna_flow_result", {}).get("state", "NEUTRAL")
        momentum = agent_data["data"].get("agent_a", {}).get("signal", "NEUTRAL")
        flip_level = agent_data["data"].get("gamma_flip_level")

        # 2. Transform via Presenters
        ui_state = {
            "micro_stats": MicroStatsPresenter.build(
                gex_regime=gex_regime,
                wall_dyn=micro.get("wall_migration", {}),
                vanna=vanna_state,
                momentum=momentum
            ),
            "wall_migration": WallMigrationPresenter.build(
                wall_migration=micro.get("wall_migration", {})
            ),
            "depth_profile": DepthProfilePresenter.build(
                per_strike_gex=b_data.get("per_strike_gex", []),
                spot=spot,
                flip_level=flip_level
            ),
            "macro_volume_map": snapshot.get("volume_map", {}),
            "atm": atm_decay_payload
        }

        # 3. Inject UI state into agent payload
        agent_data["data"]["ui_state"] = ui_state

        return {
            "type": "dashboard_update",
            "timestamp": now.isoformat(),
            "spot": spot,
            "agent_g": agent_data,
        }

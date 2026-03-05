"""Unified Snapshot Builder.

Centralizes the assembly of Agent results, Data Feed snapshots,
and UI Presenter transformations into a single broadcast payload.

DESIGN: Always emits a COMPLETE payload with ui_state, never a bare
skeleton that would blank out the frontend components. If agent_data is
stale or partially missing, ui_state is built from whatever is available.
"""

import logging
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from l3_assembly.presenters.micro_stats.presenter import MicroStatsPresenter
from l3_assembly.presenters.wall_migration.presenter import WallMigrationPresenter
from l3_assembly.presenters.depth_profile.presenter import DepthProfilePresenter

logger = logging.getLogger(__name__)


class SnapshotBuilder:
    """Assembles the final WebSocket payload for the frontend.

    Invariant: every payload MUST contain a fully-populated `ui_state`
    dict. Callers must never receive a payload that would blank out the
    Wall Migration, Depth Profile, or any other persistent display.
    """

    # ── ZOMBIE-STATE FIX: Explicit null schema ─────────────────────────────────
    # Class-level constant of the COMPLETE ui_state schema with safe defaults.
    # Every payload starts from this skeleton before any real data is merged in.
    # The frontend merge spreads new data on top of previous state, so any field
    # ABSENT from a payload would never be cleared (zombie data).
    # By always emitting this skeleton, we give the frontend an explicit reset
    # signal for every field that the current tick has no data for.
    #
    # STICKY FIELDS: wall_migration, depth_profile, active_options, macro_volume_map
    # are intentionally EXCLUDED from this skeleton. Their presenters now cache
    # the last valid output and return it on empty input, so we never need to
    # emit empty arrays. Including them here would cause blanking when data is
    # transiently unavailable (the original root cause of this bug).
    UI_STATE_SKELETON: dict[str, Any] = {
        "micro_stats": {
            "net_gex":  {"label": "—", "badge": "badge-neutral"},
            "wall_dyn": {"label": "—", "badge": "badge-neutral"},
            "vanna":    {"label": "—", "badge": "badge-neutral"},
            "momentum": {"label": "—", "badge": "badge-neutral"},
        },
        # PP-STICKY FIX: tactical_triad, skew_dynamics, etc. are excluded so
        # the frontend keeps previous state when AgentG has no new data.
        # wall_migration, depth_profile, active_options, macro_volume_map are
        # also excluded — presenters cache last-valid and never return empty.
        "atm":              None,
    }

    @staticmethod
    def _get(obj, key, default=None):
        """Unified helper for dict/object access."""
        if hasattr(obj, key): return getattr(obj, key, default)
        if isinstance(obj, dict): return obj.get(key, default)
        return default

    @staticmethod
    def build(
        snapshot: dict[str, Any] | Any,
        agent_result: Any,
        atm_decay_payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Convert raw agent outputs into a structured UI payload.

        Always produces a complete ui_state. On error or partial data,
        Presenters are still called with whatever is available, which
        returns their own zero-state rather than omitting the field.
        """
        now = datetime.now(ZoneInfo("US/Eastern"))
        _get = SnapshotBuilder._get
        spot = _get(snapshot, "spot")

        # Safely extract agent data — never short-circuit before building ui_state
        # PP-L3G FIX: Use mode='json' to ensure datetime objects are stringified.
        # This prevents TypeError in jsonpatch.make_patch during broadcast/shutdown.
        agent_data = agent_result.model_dump(mode='json') if agent_result else {}

        # RACE FIX (Race 4): We avoid mutating the original pydantic dump by
        # creating a shallow copy of the data_block before injecting ui_state.
        data_block = agent_data.get("data") or {}
        b_data = data_block.get("agent_b", {}).get("data") or {}
        micro = (b_data.get("micro_structure") or {}).get("micro_structure_state") or {}
        
        gex_regime = data_block.get("gex_regime") or "NEUTRAL"
        vanna_state = (micro.get("vanna_flow_result") or {}).get("state") or "NEUTRAL"
        momentum = (data_block.get("agent_a") or {}).get("signal") or "NEUTRAL"
        flip_level = data_block.get("gamma_flip_level")

        # Build the SnapshotBuilder-exclusive ui components
        # (wall_migration and depth_profile require raw snapshot data not available inside AgentG)
        sb_additions = {
            "wall_migration": WallMigrationPresenter.build(
                wall_migration=micro.get("wall_migration") or {},
            ),
            "depth_profile": DepthProfilePresenter.build(
                per_strike_gex=b_data.get("per_strike_gex") or [],
                spot=spot,
                flip_level=flip_level,
            ),
            "macro_volume_map": _get(snapshot, "volume_map") or {},
            "atm": atm_decay_payload,
        }

        logger.debug(
            f"[SnapshotBuilder] wall_migration rows={len(sb_additions['wall_migration'])}, "
            f"depth_profile rows={len(sb_additions['depth_profile'])}, "
            f"per_strike_gex_raw={len(b_data.get('per_strike_gex') or [])}"
        )

        # MERGE strategy (3-layer):
        # 1. Start with UI_STATE_SKELETON — explicit nulls for every optional field.
        # 2. Overlay AgentG's existing ui_state (tactical_triad, skew_dynamics, etc.).
        # 3. Overlay SnapshotBuilder's own additions (wall_migration, depth_profile).
        # Net effect: new data wins; absent optional fields fall back to explicit null/[].
        if data_block:
            # Create a new data block dict to avoid mutating the original in-place
            new_data_block = dict(data_block)
            existing_ui = data_block.get("ui_state") or {}
            
            new_data_block["ui_state"] = {
                **SnapshotBuilder.UI_STATE_SKELETON,
                **existing_ui,
                **sb_additions,
            }

            dp = new_data_block["ui_state"].get("depth_profile", [])
            strikes = [r.get("strike") for r in dp]
            if len(strikes) != len(set(strikes)):
                logger.error(f"[SnapshotBuilder] DUPLICATE STRIKES DETECTED in depth_profile: {strikes}")

            agent_data["data"] = new_data_block
        else:
            agent_data["data"] = {
                "ui_state": {**SnapshotBuilder.UI_STATE_SKELETON, **sb_additions}
            }
            new_data_block = agent_data["data"]
            
            dp = new_data_block["ui_state"].get("depth_profile", [])
            strikes = [r.get("strike") for r in dp]
            if len(strikes) != len(set(strikes)):
                logger.error(f"[SnapshotBuilder] DUPLICATE STRIKES DETECTED in depth_profile: {strikes}")

        # PP-3 FIX: Detect OOD (Out-of-Date) Tick Drift between L0 snapshot and L2 agent decision
        snapshot_time = snapshot.get("as_of")
        agent_as_of = data_block.get("as_of")
        
        drift_warning = False
        drift_ms = 0.0
        
        try:
            if isinstance(snapshot_time, str):
                snapshot_time = datetime.fromisoformat(snapshot_time)
            if isinstance(agent_as_of, str):
                agent_as_of = datetime.fromisoformat(agent_as_of)
                
            if snapshot_time and agent_as_of:
                delay = (agent_as_of - snapshot_time).total_seconds()
                drift_ms = delay * 1000
                if delay > 0.8:
                    drift_warning = True
        except Exception as e:
            logger.debug(f"[L3 SnapshotBuilder] Failed to calc drift: {e}")

        return {
            "type": "dashboard_update",
            "data_timestamp": now.isoformat(),
            "broadcast_timestamp": now.isoformat(),
            "spot": spot,
            "drift_ms": drift_ms,
            "drift_warning": drift_warning,
            "agent_g": agent_data,
        }

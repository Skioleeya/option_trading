"""MicroStats submodule — Presenter.

将 Agent 业务数据转化为前端渲染所需的 UI 状态字典。
无 if/else 颜色判断，全部通过字典查找委托给 mappings.py。
"""

from typing import Any
from app.ui.micro_stats import mappings, thresholds


# PP-L3C FIX: Debounce state for wall_key so a single-tick PINCH⇄SIEGE
# oscillation caused by REINFORCED_WALL entering/leaving its state
# does not immediately flip the MicroStats badge.
#
# Only commit a new wall_key if it has been stable for >= _WALL_KEY_DEBOUNCE_TICKS.
_last_committed_wall_key: str = "STABLE"
_pending_wall_key: str = ""
_pending_wall_key_count: int = 0
_WALL_KEY_DEBOUNCE_TICKS: int = 2  # must see same key this many times before committing


class MicroStatsPresenter:

    @classmethod
    def build(
        cls,
        gex_regime: str,
        wall_dyn: dict[str, Any],
        vanna: str,
        momentum: str,
    ) -> dict[str, Any]:
        """Build the MicroStats UI state block for the frontend.

        Args:
            gex_regime: Raw regime string from VannaFlowResult (SUPER_PIN / DAMPING / ACCELERATION / NEUTRAL).
            wall_dyn:   WallMigration micro_structure_state dict (含 call_wall_state / put_wall_state).
            vanna:      Raw vanna state string (DANGER_ZONE / GRIND_STABLE / VANNA_FLIP / NORMAL / UNAVAILABLE).
            momentum:   Agent A signal (BULLISH / BEARISH / NEUTRAL).
        """
        # Strip Enum prefix if present
        gex_regime = str(gex_regime or "NEUTRAL")
        if "." in gex_regime: gex_regime = gex_regime.split(".")[-1]

        vanna = str(vanna or "NORMAL")
        if "." in vanna: vanna = vanna.split(".")[-1]

        momentum = str(momentum or "NEUTRAL")
        if "." in momentum: momentum = momentum.split(".")[-1]

        # ─── 1. Wall dynamics composite key ─────────────────────────────────
        # (priority: PINCH > SIEGE > RETREAT > COLLAPSE > STABLE)
        global _last_committed_wall_key, _pending_wall_key, _pending_wall_key_count
        call_st = str(wall_dyn.get("call_wall_state", "") if wall_dyn else "")
        put_st  = str(wall_dyn.get("put_wall_state",  "") if wall_dyn else "")

        if "." in call_st: call_st = call_st.split(".")[-1]
        if "." in put_st:  put_st  = put_st.split(".")[-1]


        # 优先级：PINCH > SIEGE > RETREAT > COLLAPSE > STABLE
        if (call_st in thresholds.WALL_PINCH_CALL_STATES and
                put_st in thresholds.WALL_PINCH_PUT_STATES):
            candidate_key = "PINCH"
        elif call_st in thresholds.WALL_SIEGE_STATES or put_st in thresholds.WALL_SIEGE_STATES:
            candidate_key = "SIEGE"
        elif call_st in thresholds.WALL_RETREAT_STATES:
            candidate_key = "RETREAT"
        elif put_st in thresholds.WALL_COLLAPSE_STATES:
            candidate_key = "COLLAPSE"
        else:
            candidate_key = "STABLE"

        # PP-L3C: Debounce — only commit when candidate is stable for N ticks.
        if candidate_key == _pending_wall_key:
            _pending_wall_key_count += 1
        else:
            _pending_wall_key = candidate_key
            _pending_wall_key_count = 1  # reset counter, first observed tick

        if _pending_wall_key_count >= _WALL_KEY_DEBOUNCE_TICKS:
            _last_committed_wall_key = _pending_wall_key

        wall_key = _last_committed_wall_key

        # ─── 2. 查表组装 UI 状态 ──────────────────────────────────────────
        return {
            "net_gex":  mappings.GEX_REGIME_MAP.get(
                gex_regime, mappings.GEX_REGIME_MAP["NEUTRAL"]
            ),
            "wall_dyn": mappings.WALL_DYNAMICS_MAP.get(
                wall_key, mappings.WALL_DYNAMICS_MAP["STABLE"]
            ),
            "vanna":    mappings.VANNA_STATE_MAP.get(
                vanna, mappings.VANNA_STATE_MAP["NORMAL"]
            ),
            "momentum": mappings.MOMENTUM_MAP.get(
                momentum, mappings.MOMENTUM_MAP["NEUTRAL"]
            ),
        }

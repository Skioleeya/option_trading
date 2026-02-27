"""MicroStats submodule — Presenter.

将 Agent 业务数据转化为前端渲染所需的 UI 状态字典。
无 if/else 颜色判断，全部通过字典查找委托给 mappings.py。
"""

from typing import Any
from app.ui.micro_stats import mappings, thresholds


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
        # ─── 1. WALL DYN 状态聚合 ─────────────────────────────────────────
        # 从原始 call/put wall 状态推导出单一的 UI 展示状态
        call_st = wall_dyn.get("call_wall_state", "") if wall_dyn else ""
        put_st  = wall_dyn.get("put_wall_state",  "") if wall_dyn else ""

        # 优先级：PINCH > SIEGE > RETREAT > COLLAPSE > STABLE
        if (call_st in thresholds.WALL_PINCH_CALL_STATES and
                put_st in thresholds.WALL_PINCH_PUT_STATES):
            wall_key = "PINCH"
        elif call_st in thresholds.WALL_SIEGE_STATES or put_st in thresholds.WALL_SIEGE_STATES:
            wall_key = "SIEGE"
        elif call_st in thresholds.WALL_RETREAT_STATES:
            wall_key = "RETREAT"
        elif put_st in thresholds.WALL_COLLAPSE_STATES:
            wall_key = "COLLAPSE"
        else:
            wall_key = "STABLE"

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

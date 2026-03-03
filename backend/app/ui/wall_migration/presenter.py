"""WallMigration submodule — Presenter.

Converts WallMigration micro_structure data into frontend-ready rows.
Passes state-aware lighting tokens for the 5 institutional scenarios.

COLOR PHILOSOPHY (Asian Financial Terminal Standard):
  - Pure black substrate (#060606 / #0a0a0a)
  - Red = Bullish / Upside pressure (Asian convention: 红涨)
  - Green = Bearish / Downside pressure (Asian convention: 绿跌)
  - All state glow values are calibrated to be perceived,
    not shouted — surgical neon edges only.
"""

from typing import Any
from app.ui.wall_migration import mappings, thresholds, palette


# ─── Asian Financial Terminal State Lighting ──────────────────────────────────
#
# current_border: 1px edge line on the NOW box.
# current_bg:     fill color for the NOW box.
# current_shadow: box-shadow string — confined inner neon, never washy.
# wall_dyn_badge: status text displayed right of the row.
# wall_dyn_color: badge text color (rgba with intentional opacity).
#
# Design rule: T-2 and T-1 are rendered in pure dark by the frontend.
# The backend only has authority over the NOW column light signature.
# ─────────────────────────────────────────────────────────────────────────────

_CALL_STATE_LIGHTING: dict[str, dict[str, str]] = {
    # ⚡ BREACHED — White-hot alarm. Call wall pierced, gamma squeeze active.
    # Border: near-white surgical edge. BG: pitch black to maximise contrast.
    # Shadow: tight 8px outer corona, bright inner fill.
    "BREACHED": {
        "border":         "rgba(250, 250, 250, 0.85)",
        "bg":             "rgba(10, 10, 10, 0.95)",
        "shadow":         "0 0 10px rgba(250,250,250,0.45), inset 0 0 8px rgba(250,250,250,0.10)",
        "wall_dyn_badge": "BREACHED",
        "wall_dyn_color": "rgba(250, 250, 250, 0.95)",
    },
    # ☄️ RETREATING_RESISTANCE — Call wall lifted. Bullish corridor opens.
    # Badge amber: transition / momentum colour used pan-Asian for "movement".
    "RETREATING_RESISTANCE": {
        "border":         "rgba(234, 179, 8, 0.55)",
        "bg":             "rgba(66, 32, 6, 0.45)",
        "shadow":         "0 0 8px rgba(234,179,8,0.25), inset 0 0 5px rgba(234,179,8,0.08)",
        "wall_dyn_badge": "RETREAT ↑",
        "wall_dyn_color": "rgba(234, 179, 8, 0.90)",
    },
    # 🩸 REINFORCED_WALL — Call wall reinforced. Ceiling locked, dealers short.
    # Muted red edge — no neon screaming, just a cold hard jaw.
    "REINFORCED_WALL": {
        "border":         "rgba(239, 68, 68, 0.45)",
        "bg":             "rgba(69, 10, 10, 0.40)",
        "shadow":         "inset 0 0 10px rgba(239,68,68,0.20)",
        "wall_dyn_badge": "REINFORCED",
        "wall_dyn_color": "rgba(239, 68, 68, 0.80)",
    },
    # ⏳ DECAYING — Post 14:00 ET. Option delta decays, wall is a ghost.
    # Purple: universal signal for expired state, muted and desaturated.
    "DECAYING": {
        "border":         "rgba(161, 161, 170, 0.12)",
        "bg":             "rgba(10, 10, 10, 0.80)",
        "shadow":         "none",
        "wall_dyn_badge": "DECAYING",
        "wall_dyn_color": "rgba(113, 113, 122, 0.70)",
    },
    # 🧊 STABLE — Magnet / pinning active. Dealer delta-neutral. No edge glare.
    "STABLE": {
        "border":         "rgba(245, 158, 11, 0.40)",
        "bg":             "rgba(30, 22, 4, 0.50)",
        "shadow":         "0 0 5px rgba(245,158,11,0.12)",
        "wall_dyn_badge": "STABLE",
        "wall_dyn_color": "rgba(161, 161, 170, 0.55)",
    },
    "UNAVAILABLE": {
        "border":         "rgba(255, 255, 255, 0.06)",
        "bg":             "rgba(10, 10, 10, 0.60)",
        "shadow":         "none",
        "wall_dyn_badge": "—",
        "wall_dyn_color": "rgba(82, 82, 91, 0.80)",
    },
}

_PUT_STATE_LIGHTING: dict[str, dict[str, str]] = {
    # ⚡ BREACHED — Put wall pierced. Spot fell through floor. Panic cascade.
    "BREACHED": {
        "border":         "rgba(250, 250, 250, 0.85)",
        "bg":             "rgba(10, 10, 10, 0.95)",
        "shadow":         "0 0 10px rgba(250,250,250,0.45), inset 0 0 8px rgba(250,250,250,0.10)",
        "wall_dyn_badge": "BREACHED",
        "wall_dyn_color": "rgba(250, 250, 250, 0.95)",
    },
    # ☄️ RETREATING_SUPPORT — Put wall moved lower. Support retreating. Bearish.
    "RETREATING_SUPPORT": {
        "border":         "rgba(234, 179, 8, 0.55)",
        "bg":             "rgba(6, 40, 22, 0.45)",
        "shadow":         "0 0 8px rgba(234,179,8,0.25), inset 0 0 5px rgba(234,179,8,0.08)",
        "wall_dyn_badge": "RETREAT ↓",
        "wall_dyn_color": "rgba(234, 179, 8, 0.90)",
    },
    # 🍏 REINFORCED_SUPPORT — Put wall holding. Floor locked. Dealers long puts.
    "REINFORCED_SUPPORT": {
        "border":         "rgba(16, 185, 129, 0.45)",
        "bg":             "rgba(2, 44, 34, 0.40)",
        "shadow":         "inset 0 0 10px rgba(16,185,129,0.20)",
        "wall_dyn_badge": "REINFORCED",
        "wall_dyn_color": "rgba(16, 185, 129, 0.80)",
    },
    # ⏳ DECAYING
    "DECAYING": {
        "border":         "rgba(161, 161, 170, 0.12)",
        "bg":             "rgba(10, 10, 10, 0.80)",
        "shadow":         "none",
        "wall_dyn_badge": "DECAYING",
        "wall_dyn_color": "rgba(113, 113, 122, 0.70)",
    },
    # 🧊 STABLE
    "STABLE": {
        "border":         "rgba(245, 158, 11, 0.40)",
        "bg":             "rgba(30, 22, 4, 0.50)",
        "shadow":         "0 0 5px rgba(245,158,11,0.12)",
        "wall_dyn_badge": "STABLE",
        "wall_dyn_color": "rgba(161, 161, 170, 0.55)",
    },
    "UNAVAILABLE": {
        "border":         "rgba(255, 255, 255, 0.06)",
        "bg":             "rgba(10, 10, 10, 0.60)",
        "shadow":         "none",
        "wall_dyn_badge": "—",
        "wall_dyn_color": "rgba(82, 82, 91, 0.80)",
    },
}


class WallMigrationPresenter:

    @classmethod
    def build(cls, wall_migration: dict[str, Any]) -> list[dict[str, Any]]:
        """Build the WallMigration row list for the frontend with 5-scenario lighting."""
        if not wall_migration:
            return []

        n = thresholds.HISTORY_DEPTH

        call_hist = wall_migration.get("call_wall_history", [])
        put_hist  = wall_migration.get("put_wall_history",  [])

        call_state_str = str(wall_migration.get("call_wall_state", "UNAVAILABLE") or "UNAVAILABLE")
        put_state_str  = str(wall_migration.get("put_wall_state",  "UNAVAILABLE") or "UNAVAILABLE")

        # Strip Enum prefix if present (e.g. 'WallMigrationCallState.STABLE' -> 'STABLE')
        if "." in call_state_str: call_state_str = call_state_str.split(".")[-1]
        if "." in put_state_str:  put_state_str  = put_state_str.split(".")[-1]

        call_lights = _CALL_STATE_LIGHTING.get(call_state_str, _CALL_STATE_LIGHTING["UNAVAILABLE"])
        put_lights  = _PUT_STATE_LIGHTING.get(put_state_str,   _PUT_STATE_LIGHTING["UNAVAILABLE"])

        def _pad(hist: list, depth: int) -> list:
            total = depth + 1
            if len(hist) >= total:
                return hist[-total:]
            return [None] * (total - len(hist)) + hist

        call_padded = _pad(call_hist, n)
        put_padded  = _pad(put_hist,  n)

        def _row(padded, row_template: dict, lights: dict, state: str) -> dict[str, Any]:
            return {
                **row_template,
                **{f"h{i + 1}": padded[i] for i in range(n)},
                "current":        padded[-1],
                "current_border": lights["border"],
                "current_bg":     lights["bg"],
                "current_shadow": lights["shadow"],
                "current_text":   "text-white font-bold",   # frontend overrides per state
                "current_pulse":  "pulse" if state == "BREACHED" else "none",
                "wall_dyn_badge": lights["wall_dyn_badge"],
                "wall_dyn_color": lights["wall_dyn_color"],
                "state":          state,
            }

        return [
            _row(call_padded, mappings.CALL_ROW, call_lights, call_state_str),
            _row(put_padded,  mappings.PUT_ROW,  put_lights,  put_state_str),
        ]

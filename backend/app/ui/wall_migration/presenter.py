"""WallMigration submodule — Presenter.

Converts WallMigration micro_structure data into frontend-ready rows.
No hardcoded colors. No magic numbers. All constants in thresholds/mappings.
"""

from typing import Any
from app.ui.wall_migration import mappings, thresholds


class WallMigrationPresenter:

    @classmethod
    def build(cls, wall_migration: dict[str, Any]) -> list[dict[str, Any]]:
        """Build the WallMigration row list for the frontend.

        Args:
            wall_migration: Raw wall migration dict from micro_structure_state.

        Returns:
            Two-element list: [call_row, put_row], each with typed CSS bindings.
        """
        if not wall_migration:
            return []

        n = thresholds.HISTORY_DEPTH

        call_hist = wall_migration.get("call_wall_history", [])
        put_hist  = wall_migration.get("put_wall_history", [])

        def _pad(hist: list, depth: int) -> list:
            """Pad or trim to exactly `depth` history + 1 current slot."""
            total = depth + 1
            if len(hist) >= total:
                return hist[-total:]
            return [None] * (total - len(hist)) + hist

        call_padded = _pad(call_hist, n)
        put_padded  = _pad(put_hist,  n)

        def _row(padded, label, bg, text, dot) -> dict[str, Any]:
            return {
                "type_label": label,
                "type_bg":    bg,
                "type_text":  text,
                **{f"h{i + 1}": padded[i] for i in range(n)},
                "current":    padded[-1],
                "dot_color":  dot,
            }

        return [
            _row(call_padded,
                 mappings.CALL_TYPE_LABEL, mappings.CALL_TYPE_BG,
                 mappings.CALL_TYPE_TEXT,  mappings.CALL_DOT_COLOR),
            _row(put_padded,
                 mappings.PUT_TYPE_LABEL,  mappings.PUT_TYPE_BG,
                 mappings.PUT_TYPE_TEXT,   mappings.PUT_DOT_COLOR),
        ]

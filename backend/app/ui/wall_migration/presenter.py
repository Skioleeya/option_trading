"""WallMigration submodule — Presenter.

Converts WallMigration micro_structure data into frontend-ready rows.
All colors come from this submodule's own palette.
"""

from typing import Any
from app.ui.wall_migration import mappings, thresholds, palette


class WallMigrationPresenter:

    @classmethod
    def build(cls, wall_migration: dict[str, Any]) -> list[dict[str, Any]]:
        """Build the WallMigration row list for the frontend."""
        if not wall_migration:
            return []

        n = thresholds.HISTORY_DEPTH

        call_hist = wall_migration.get("call_wall_history", [])
        put_hist  = wall_migration.get("put_wall_history",  [])

        def _pad(hist: list, depth: int) -> list:
            total = depth + 1
            if len(hist) >= total:
                return hist[-total:]
            return [None] * (total - len(hist)) + hist

        call_padded = _pad(call_hist, n)
        put_padded  = _pad(put_hist,  n)

        def _row(padded, row_template: dict) -> dict[str, Any]:
            return {
                **row_template,
                **{f"h{i + 1}": padded[i] for i in range(n)},
                "current": padded[-1],
                # Pass palette constants for the current-box highlight
                "current_border": palette.CURRENT_BOX_BORDER,
                "current_bg":     palette.CURRENT_BOX_BG,
                "current_shadow": palette.CURRENT_BOX_SHADOW,
                "current_text":   palette.CURRENT_TEXT_CLASS,
            }

        return [
            _row(call_padded, mappings.CALL_ROW),
            _row(put_padded,  mappings.PUT_ROW),
        ]

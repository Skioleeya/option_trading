"""Presenter for the WallMigration frontend component."""

from typing import Any
from app.ui import theme

class WallMigrationPresenter:
    """Format business data into WallMigration UI state."""

    @classmethod
    def build(cls, wall_migration: dict[str, Any]) -> list[dict[str, Any]]:
        """Calculates frontend color and styling bindings for Wall Migration.
        
        Args:
            wall_migration: Wall migration structured data from Agent B1.
            
        Returns:
            List of row dictionaries for the frontend to strictly render.
        """
        if not wall_migration:
            return []

        call_hist = wall_migration.get("call_wall_history", [])
        put_hist = wall_migration.get("put_wall_history", [])
        
        # Ensure we have exactly 3 items for rendering: [h1, h2, current]
        # Pad with Nones if necessary
        call_padded = call_hist[-3:] if len(call_hist) >= 3 else [None] * (3 - len(call_hist)) + call_hist
        put_padded = put_hist[-3:] if len(put_hist) >= 3 else [None] * (3 - len(put_hist)) + put_hist

        rows = []
        
        # Call Row
        rows.append({
            "type_label": "C",
            "type_bg": theme.BG_WALL_CALL,
            "type_text": theme.MARKET_UP,
            "h1": call_padded[0],
            "h2": call_padded[1],
            "current": call_padded[2],
            "dot_color": theme.ACCENT_RED
        })
        
        # Put Row
        rows.append({
            "type_label": "P",
            "type_bg": theme.BG_WALL_PUT,
            "type_text": theme.MARKET_DOWN,
            "h1": put_padded[0],
            "h2": put_padded[1],
            "current": put_padded[2],
            "dot_color": theme.ACCENT_GREEN
        })

        return rows

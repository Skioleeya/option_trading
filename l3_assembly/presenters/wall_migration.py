"""l3_assembly.presenters.wall_migration — WallMigrationPresenterV2.

Wraps the legacy WallMigrationPresenter (5-scenario lighting + sticky cache)
and returns list[WallMigrationRow] instead of list[dict].

The sticky-cache (_last_valid_wall) behaviour is preserved — we call the
legacy presenter directly so its module-level state is shared.
"""

from __future__ import annotations

from typing import Any

from l3_assembly.events.payload_events import WallMigrationRow


class WallMigrationPresenterV2:
    """Strongly-typed WallMigration presenter."""

    @classmethod
    def build(
        cls,
        wall_migration: dict[str, Any],
    ) -> tuple[WallMigrationRow, ...]:
        """Return typed tuple of WallMigrationRow.

        Delegates to legacy presenter for lighting computation and sticky-cache
        behaviour.  Parses the resulting dicts into typed WallMigrationRow.
        """
        try:
            from l3_assembly.presenters.ui.wall_migration.presenter import WallMigrationPresenter
            raw_rows: list[dict[str, Any]] = WallMigrationPresenter.build(
                wall_migration=wall_migration,
            )
        except ImportError as e:
            import logging
            logging.getLogger(__name__).error(f"WallMigrationPresenterV2 ImportError: {e}")
            raw_rows = []

        return tuple(cls._row_from_dict(r) for r in raw_rows if r)

    @staticmethod
    def _row_from_dict(d: dict[str, Any]) -> WallMigrationRow:
        history = []
        for i in range(1, 10):
            if f"h{i}" in d and d[f"h{i}"] is not None:
                history.append(float(d[f"h{i}"]))
        
        lights = {
            "current_border": str(d.get("current_border", "")),
            "current_bg": str(d.get("current_bg", "")),
            "current_shadow": str(d.get("current_shadow", "")),
            "current_text": str(d.get("current_text", "")),
            "current_pulse": str(d.get("current_pulse", "")),
            "wall_dyn_badge": str(d.get("wall_dyn_badge", "")),
            "wall_dyn_color": str(d.get("wall_dyn_color", "")),
            "type_bg": str(d.get("type_bg", "")),
            "type_text": str(d.get("type_text", "")),
            "dot_color": str(d.get("dot_color", "")),
        }
        
        return WallMigrationRow(
            label=str(d.get("type_label", "")),
            strike=float(d.get("current", 0.0) or 0.0),
            state=str(d.get("state", "UNAVAILABLE")),
            history=history,
            lights={k: v for k, v in lights.items() if v},
        )

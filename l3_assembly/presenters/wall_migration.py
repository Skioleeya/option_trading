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
        except ImportError:
            raw_rows = []

        return tuple(cls._row_from_dict(r) for r in raw_rows if r)

    @staticmethod
    def _row_from_dict(d: dict[str, Any]) -> WallMigrationRow:
        return WallMigrationRow(
            label=str(d.get("label", "")),
            strike=float(d.get("strike", 0.0) or 0.0),
            state=str(d.get("state", "UNAVAILABLE")),
            history=list(d.get("history", [])),
            lights={k: str(v) for k, v in (d.get("lights") or {}).items()},
        )

"""l3_assembly.presenters.skew_dynamics — SkewDynamicsPresenterV2.

Pass-through adapter. The skew_dynamics presenter output remains a
dict for now (full typing deferred to Phase 2.7). This adapter ensures
a consistent interface with the other V2 presenters.
"""

from __future__ import annotations

from typing import Any


class SkewDynamicsPresenterV2:
    """Skew dynamics presenter adapter (dict pass-through)."""

    @classmethod
    def build(cls, skew_data: dict[str, Any]) -> dict[str, Any]:
        """Return skew dynamics dict (pass-through for backward compat)."""
        try:
            from l3_assembly.presenters.ui.skew_dynamics.presenter import SkewDynamicsPresenter
            return SkewDynamicsPresenter.build(skew_data=skew_data) or {}
        except (ImportError, Exception):
            # Skew dynamics may not be available in all deployment configs
            return dict(skew_data) if skew_data else {}

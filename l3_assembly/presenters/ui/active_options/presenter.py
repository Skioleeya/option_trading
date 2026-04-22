"""Compatibility wrapper for ActiveOptions service.

Kept at legacy path to avoid broad call-site churn during decoupling.
"""

from shared.services.active_options_runtime import ActiveOptionsRuntimeService


class ActiveOptionsPresenter(ActiveOptionsRuntimeService):
    """Legacy name alias backed by neutral shared runtime service."""

    pass

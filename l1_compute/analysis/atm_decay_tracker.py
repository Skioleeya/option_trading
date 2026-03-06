"""Compatibility shim for legacy imports.

Deprecated:
    Use ``l1_compute.analysis.atm_decay.tracker.AtmDecayTracker`` instead.
"""

from .atm_decay.tracker import AtmDecayTracker

__all__ = ["AtmDecayTracker"]

"""Compatibility wrapper for the legacy ATM decay import path."""

from .atm_decay.tracker import AtmDecayTracker as _AtmDecayTracker


class AtmDecayTracker(_AtmDecayTracker):
    """Legacy import-path wrapper."""


__all__ = ["AtmDecayTracker"]

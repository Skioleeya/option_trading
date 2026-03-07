"""Compatibility shim: re-export shared neutral DEGComposer classes."""

from shared.services.active_options.deg_composer import DEGComposer, InstitutionalSweepDetector

__all__ = ["DEGComposer", "InstitutionalSweepDetector"]

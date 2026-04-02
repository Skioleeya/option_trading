"""Compatibility shim: re-export shared neutral DEGComposer classes."""

from shared.services.active_options_engines import DEGComposer, InstitutionalSweepDetector

__all__ = ["DEGComposer", "InstitutionalSweepDetector"]

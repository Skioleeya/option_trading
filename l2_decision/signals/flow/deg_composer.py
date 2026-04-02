"""Compatibility shim: re-export shared neutral DEGComposer classes."""

from shared_rust.services import DEGComposer, InstitutionalSweepDetector

__all__ = ["DEGComposer", "InstitutionalSweepDetector"]

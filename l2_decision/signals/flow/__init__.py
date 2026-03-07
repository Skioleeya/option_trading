"""Compatibility exports for DEG-FLOW classes.

Concrete implementations were moved to shared.services.active_options.
"""

from .flow_engine_d import FlowEngineD
from .flow_engine_e import FlowEngineE
from .flow_engine_g import FlowEngineG
from .deg_composer import DEGComposer

__all__ = ["FlowEngineD", "FlowEngineE", "FlowEngineG", "DEGComposer"]

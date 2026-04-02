"""Compatibility exports for DEG-FLOW classes.

Concrete implementations were moved behind shared.services root-neutral surfaces.
"""

from .deg_composer import DEGComposer
from .flow_engine_d import FlowEngineD
from .flow_engine_e import FlowEngineE
from .flow_engine_g import FlowEngineG

__all__ = ["FlowEngineD", "FlowEngineE", "FlowEngineG", "DEGComposer"]

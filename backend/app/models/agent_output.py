"""Typed output model for Agent B1.

Provides structured access to Agent B1's output data,
replacing deep dict.get() chains with typed attribute access.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.microstructure import MicroStructureAnalysis


class AgentB1Output(BaseModel):
    """Typed representation of Agent B1's result data.

    Used by AgentG to consume B1 output safely with proper type hints.
    """

    net_gex: float | None = None
    spy_atm_iv: float | None = None
    gamma_walls: dict[str, Any] = Field(default_factory=dict)
    gamma_flip: bool = False
    gamma_flip_level: float | None = None

    # Microstructure analysis (Agent B1 v2.0)
    micro_structure: MicroStructureAnalysis | None = None

    # Confidence values from individual trackers
    iv_confidence: float | None = None
    wall_confidence: float | None = None
    vanna_confidence: float | None = None

    # Multi-timeframe consensus
    mtf_consensus: dict[str, Any] | None = None

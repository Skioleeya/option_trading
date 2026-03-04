"""Base agent models for SPY 0DTE Dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    """Standard result container for all agents.

    Every agent (A, B1, G) returns this model so that the orchestration
    layer can consume them uniformly.
    """

    agent: str = Field(description="Agent identifier (e.g. 'agent_a', 'agent_b1', 'agent_g')")
    signal: str = Field(description="Signal output (e.g. 'BULLISH', 'BEARISH', 'NEUTRAL', 'NO_TRADE')")
    as_of: datetime = Field(description="Timestamp of the data snapshot used for this result")
    data: dict[str, Any] = Field(default_factory=dict, description="Agent-specific payload data")
    summary: str = Field(default="", description="Human-readable summary of the decision")

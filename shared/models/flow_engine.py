"""DEG-FLOW Data Contract Models.

Defines the per-strike Pydantic contracts for the DEG-FLOW engine:
  - FlowEngineInput:  what each FlowEngine_D/E/G receives per strike
  - FlowEngineOutput: what each engine produces, plus the composed DEG result

These act as the strict interface boundary between the Greeks pipeline
and the DEG composer layer, guaranteeing no NaN/None leaks downstream.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FlowEngineInput(BaseModel):
    """Per-strike input contract for all three DEG-FLOW engines.

    All fields are required.  Callers must resolve None values before
    constructing this model — use the class method `from_chain_entry`
    which applies safe defaults.
    """

    symbol: str
    option_type: Literal["CALL", "PUT"]
    strike: float
    spot: float

    # Longport snapshot fields
    volume: int = Field(ge=0)
    turnover: float = Field(ge=0.0)
    last_price: float = Field(ge=0.0)
    implied_volatility: float = Field(ge=0.0)     # decimal form, e.g. 0.142
    historical_volatility: float = Field(ge=0.0)  # decimal form from Longport HV field
    open_interest: int = Field(ge=0)

    # BSM Greeks (from GreeksExtractor)
    delta: float = 0.0
    gamma: float = 0.0
    vanna: float = 0.0   # ∂Δ/∂σ

    # Derived (passed from GreeksExtractor result)
    atm_iv: float = Field(ge=0.0, default=0.0)   # ATM IV for Moneyness normalisation

    @classmethod
    def from_chain_entry(
        cls,
        opt: dict,
        spot: float,
        atm_iv: float,
    ) -> "FlowEngineInput":
        """Safe factory that applies sensible defaults for missing fields."""
        return cls(
            symbol=opt.get("symbol", "UNKNOWN"),
            option_type="CALL" if str(opt.get("option_type", "")).upper() in ("CALL", "C") else "PUT",
            strike=float(opt.get("strike", 0) or 0),
            spot=spot,
            volume=max(0, int(opt.get("volume", 0) or 0)),
            turnover=max(0.0, float(opt.get("turnover", 0) or 0)),
            last_price=max(0.0, float(opt.get("last_price", 0) or 0)),
            implied_volatility=max(0.0, float(opt.get("implied_volatility", 0) or 0)),
            historical_volatility=max(0.0, float(opt.get("historical_volatility", 0) or 0)),
            open_interest=max(0, int(opt.get("open_interest", 0) or 0)),
            delta=float(opt.get("delta", 0) or 0),
            gamma=max(0.0, float(opt.get("gamma", 0) or 0)),
            vanna=float(opt.get("vanna", 0) or 0),
            atm_iv=max(0.0, atm_iv),
        )

    @model_validator(mode="after")
    def validate_no_nan(self) -> "FlowEngineInput":
        """Reject NaN payloads that would corrupt downstream Z-Score."""
        import math
        for field_name in ("delta", "gamma", "vanna", "implied_volatility", "historical_volatility"):
            val = getattr(self, field_name)
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"FlowEngineInput.{field_name} must be finite, got {val}")
        return self


class FlowComponentResult(BaseModel):
    """Single-engine flow result for one strike."""
    symbol: str
    strike: float
    option_type: Literal["CALL", "PUT"]
    flow_value: float   # Raw dollar value (USD)
    is_valid: bool = True
    failure_reason: str | None = None


class FlowEngineOutput(BaseModel):
    """Composed DEG-FLOW result for one strike.

    This is what ActiveOptionsPresenter consumes to produce the final UI state.
    """
    symbol: str
    option_type: Literal["CALL", "PUT"]
    strike: float
    implied_volatility: float
    volume: int
    turnover: float

    # Individual component flows (raw USD)
    flow_d: float = 0.0   # Gamma Imbalance
    flow_e: float = 0.0   # Vanna × ΔIV
    flow_g: float = 0.0   # OI Momentum

    # Z-Score normalised per-component
    flow_d_z: float = 0.0
    flow_e_z: float = 0.0
    flow_g_z: float = 0.0

    # Composite DEG score (weighted sum of z-scores)
    flow_deg: float = 0.0

    # Institutional Metrics (v4.0)
    impact_index: float = 0.0  # Option Flow Impact Index (OFII)
    is_sweep: bool = False     # Multi-strike sweep recognition flag

    # Qualitative labels derived from flow_deg
    flow_direction: Literal["BULLISH", "BEARISH", "NEUTRAL"] = "NEUTRAL"
    flow_intensity: Literal["EXTREME", "HIGH", "MODERATE", "LOW"] = "LOW"

    # Degradation flags
    engine_d_active: bool = True
    engine_e_active: bool = True
    engine_g_active: bool = True

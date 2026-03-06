"""EnrichedSnapshot — Immutable L1 → L2 output contract.

This dataclass is the canonical output of the L1 Compute Reactor.
It is frozen (immutable) to ensure L2 consumers cannot mutate state
that L1 is still managing.

Fields mirror the L1_LOCAL_COMPUTATION.md specification exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import pyarrow as pa


@dataclass(frozen=True)
class AggregateGreeks:
    """Aggregated risk exposure metrics from the full option chain."""
    net_gex: float = 0.0          # Net GEX: positive = dealer long gamma
    net_vanna: float = 0.0
    net_charm: float = 0.0
    call_wall: float = 0.0        # Strike with peak call GEX (resistance)
    call_wall_gex: float = 0.0
    put_wall: float = 0.0         # Strike with peak put GEX (support)
    put_wall_gex: float = 0.0
    flip_level: float = 0.0       # Strike nearest GEX sign change
    atm_iv: float = 0.0           # IV of nearest-ATM option
    total_call_gex: float = 0.0
    total_put_gex: float = 0.0
    num_contracts: int = 0
    per_strike_gex: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class MicroSignals:
    """Microstructure signals: VPIN, BBO, Volume Acceleration, and Flow Trackers."""
    # VPIN
    vpin_1m: float = 0.0
    vpin_5m: float = 0.0
    vpin_15m: float = 0.0
    vpin_composite: float = 0.0
    vpin_regime: str = "NORMAL"    # NORMAL / ELEVATED / TOXIC

    # BBO Imbalance
    bbo_imbalance_raw: float = 0.0
    bbo_ewma_fast: float = 0.0
    bbo_ewma_slow: float = 0.0
    bbo_persistence: float = 0.0

    # Volume Acceleration
    vol_accel_ratio: float = 0.0
    vol_accel_threshold: float = 2.0
    vol_accel_elevated: bool = False
    vol_entropy: float = 0.0
    session_phase: str = "mid"
    
    # IV Velocity & MTF
    iv_velocity: Optional[dict[str, Any]] = None
    mtf_consensus: Optional[dict[str, Any]] = None
    iv_confidence: float = 0.0
    
    # Wall Migration
    wall_migration: Optional[dict[str, Any]] = None
    wall_confidence: float = 0.0
    
    # Vanna Flow
    vanna_flow_result: Optional[dict[str, Any]] = None
    vanna_confidence: float = 0.0
    
    # Volume Imbalance (Phase 24)
    volume_imbalance: Optional[dict[str, Any]] = None
    
    # Jump Detection (Phase 27)
    jump_detection: Optional[dict[str, Any]] = None
    
    # Squeeze Alerts
    dealer_squeeze_alert: bool = False
    avg_atm_vpin_score: float = 0.0


@dataclass(frozen=True)
class ComputeQualityReport:
    """Computation diagnostics for L1 quality monitoring."""
    contracts_computed: int = 0
    contracts_skipped: int = 0       # Missing IV or invalid inputs
    nan_count: int = 0
    compute_tier: str = "numpy"      # gpu | numba | numpy
    greeks_latency_ms: float = 0.0
    aggregation_latency_ms: float = 0.0
    # IV resolution source distribution
    iv_ws_count: int = 0
    iv_rest_count: int = 0
    iv_chain_count: int = 0
    iv_sabr_count: int = 0
    iv_missing_count: int = 0
    # SABR calibration
    sabr_calibrated: bool = False
    sabr_rmse: float = 0.0


@dataclass(frozen=True)
class EnrichedSnapshot:
    """Immutable L1 compute output — canonical L1 → L2 contract.

    All L2 Decision Layer consumers receive this object.
    Immutability prevents unintentional state mutation across layers.

    Fields:
        spot:           Underlying spot price at compute time.
        aggregates:     Full chain aggregated risk (GEX, walls, etc.).
        microstructure: VPIN + BBO + Volume Acceleration signals.
        quality:        Computation diagnostics and IV source breakdown.
        atm_iv:         ATM implied volatility (convenience accessor).
        ttm_seconds:    Precise remaining trading seconds (from TTM v2).
        version:        L0 MVCC snapshot version used for computation.
        computed_at:    Wall-clock time of computation completion.
    """
    spot: float
    chain: Any  # Accept pa.RecordBatch or fallback
    aggregates: AggregateGreeks
    microstructure: MicroSignals
    quality: ComputeQualityReport
    ttm_seconds: float
    version: int
    computed_at: datetime
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def atm_iv(self) -> float:
        return self.aggregates.atm_iv

    @property
    def net_gex(self) -> float:
        return self.aggregates.net_gex

    @property
    def call_wall(self) -> float:
        return self.aggregates.call_wall

    @property
    def put_wall(self) -> float:
        return self.aggregates.put_wall

    @property
    def flip_level(self) -> float:
        return self.aggregates.flip_level

    @property
    def per_strike_gex(self) -> list[dict]:
        return self.aggregates.per_strike_gex

    def to_legacy_dict(self) -> dict:
        """Compatibility shim: produce the dict schema consumed by existing agents.

        Allows gradual migration without breaking agent_b.py, agent_g.py, etc.
        """
        # Expose the chain items properly back to dictionaries if caller requires:
        if isinstance(self.chain, pa.RecordBatch):
            chain_elements = self.chain.to_pylist()
        else:
            chain_elements = list(self.chain) if self.chain else []

        return {
            "net_gex":        self.aggregates.net_gex,
            "net_vanna":      self.aggregates.net_vanna,
            "net_charm":      self.aggregates.net_charm,
            "call_wall":      self.aggregates.call_wall,
            "put_wall":       self.aggregates.put_wall,
            "flip_level":     self.aggregates.flip_level,
            "atm_iv":         self.aggregates.atm_iv,
            "total_call_gex": self.aggregates.total_call_gex,
            "total_put_gex":  self.aggregates.total_put_gex,
            "spy_atm_iv":     self.aggregates.atm_iv,
            "vpin_score":     self.microstructure.vpin_composite,
            "bbo_imbalance":  self.microstructure.bbo_imbalance_raw,
            "vol_accel_ratio": self.microstructure.vol_accel_ratio,
            "ttm_seconds":    self.ttm_seconds,
            "version":        self.version,
            "computed_at":    self.computed_at.isoformat(),
            "chain_elements": chain_elements,
            "per_strike_gex": chain_elements,  # Map full chain as strike info
            "spot":           self.spot,
            # Refactor: Phase 1 microstructure outputs
            "microstructure": self.microstructure,
            # Extra metadata (e.g. rust_active)
            **self.extra_metadata,
        }

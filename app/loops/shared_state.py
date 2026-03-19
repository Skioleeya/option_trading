"""Shared state between asynchronous loops.

Decouples the compute loop (which writes state) from the broadcast
and housekeeping loops (which read state).
"""

import time
from typing import Any
from dataclasses import dataclass, field

from l3_assembly.events.payload_events import FrozenPayload


@dataclass(frozen=True)
class ActiveOptionsInputSnapshot:
    """Single-source ActiveOptions input published by compute loop."""

    chain: list[dict[str, Any]] = field(default_factory=list)
    spot: float = 0.0
    atm_iv: float = 0.0
    gex_regime: str = "NEUTRAL"
    ttm_seconds: float | None = None
    source_version: int = 0
    source_timestamp_utc: str | None = None
    valid: bool = False
    invalid_reason: str | None = None


@dataclass
class SharedLoopState:
    """State blackboard for asynchronous tasks."""
    
    frozen: FrozenPayload | None = None
    payload_dict: dict[str, Any] | None = None
    latest_l1_snapshot: Any | None = None
    latest_active_options_input: ActiveOptionsInputSnapshot | None = None
    last_payload_time: float = 0.0
    last_active_options_input_time: float = 0.0
    
    # Trackers for diagnostics
    total_computations: int = 0
    failed_computations: int = 0
    active_options_input_updates: int = 0
    current_compute_interval: float = 1.0
    snapshot_version_iv_probe: dict[str, Any] = field(default_factory=dict)
    compute_ticks_seen: int = 0
    duplicate_snapshot_skips: int = 0
    l1_compute_runs: int = 0
    last_snapshot_version: int | None = None
    last_compute_id: int = 0
    last_gpu_task_id: str | None = None

    def update(self, frozen: FrozenPayload, spot: float | None = None) -> None:
        """Atomically update the payload state."""
        self.frozen = frozen
        self.payload_dict = frozen.to_dict()
        self.last_payload_time = time.monotonic()
        self.total_computations += 1

    def record_failure(self) -> None:
        """Record a computation loop failure."""
        self.failed_computations += 1

    def update_snapshot_version_iv_probe(self, diagnostics: dict[str, Any]) -> None:
        """Publish snapshot_version vs spy_atm_iv probe diagnostics."""
        self.snapshot_version_iv_probe = diagnostics

    def update_latest_l1_snapshot(self, snapshot: Any) -> None:
        """Publish latest L1 snapshot for auxiliary loops (housekeeping)."""
        self.latest_l1_snapshot = snapshot

    def update_active_options_input(self, snapshot: ActiveOptionsInputSnapshot) -> None:
        """Publish compute-loop normalized input for ActiveOptions runtime path."""
        self.latest_active_options_input = snapshot
        self.last_active_options_input_time = time.monotonic()
        self.active_options_input_updates += 1

    def record_compute_tick(self, snapshot_version: int) -> None:
        """Record one compute-loop tick before dedup decision."""
        self.compute_ticks_seen += 1
        self.last_snapshot_version = snapshot_version

    def record_duplicate_snapshot_skip(self, snapshot_version: int) -> None:
        """Record one deduplicated snapshot tick (L1/L2 skipped)."""
        self.duplicate_snapshot_skips += 1
        self.last_snapshot_version = snapshot_version

    def record_l1_compute(
        self,
        *,
        snapshot_version: int,
        compute_id: int,
        gpu_task_id: str | None,
    ) -> None:
        """Record one executed L1 compute dispatch."""
        self.l1_compute_runs += 1
        self.last_snapshot_version = snapshot_version
        self.last_compute_id = compute_id
        self.last_gpu_task_id = gpu_task_id

    @property
    def is_running(self) -> bool:
        """Check if we have recent computations."""
        return self.last_payload_time > 0
    
    def get_diagnostics(self) -> dict[str, Any]:
        """Return agent runner diagnostics."""
        age = time.monotonic() - self.last_payload_time if self.last_payload_time else None
        input_age = (
            time.monotonic() - self.last_active_options_input_time
            if self.last_active_options_input_time
            else None
        )
        active_options_input = self.latest_active_options_input
        input_chain_size = (
            len(active_options_input.chain)
            if active_options_input is not None
            else 0
        )
        total = self.total_computations + self.failed_computations
        return {
            "total_computations": self.total_computations,
            "failed_computations": self.failed_computations,
            "success_rate": (self.total_computations / total * 100) if total > 0 else 100.0,
            "last_update_age_seconds": age,
            "is_running": self.is_running,
            "snapshot_version_iv_probe": self.snapshot_version_iv_probe,
            "active_options_input": {
                "updates": self.active_options_input_updates,
                "age_seconds": input_age,
                "valid": bool(active_options_input.valid) if active_options_input else False,
                "chain_size": input_chain_size,
                "source_version": int(active_options_input.source_version) if active_options_input else 0,
                "source_timestamp_utc": active_options_input.source_timestamp_utc if active_options_input else None,
                "invalid_reason": active_options_input.invalid_reason if active_options_input else "missing_input",
            },
            "gpu_compute_audit": {
                "compute_ticks_seen": self.compute_ticks_seen,
                "duplicate_snapshot_skips": self.duplicate_snapshot_skips,
                "l1_compute_runs": self.l1_compute_runs,
                "last_snapshot_version": self.last_snapshot_version,
                "last_compute_id": self.last_compute_id,
                "last_gpu_task_id": self.last_gpu_task_id,
            },
        }

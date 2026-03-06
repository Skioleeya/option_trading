"""Shared state between asynchronous loops.

Decouples the compute loop (which writes state) from the broadcast
and housekeeping loops (which read state).
"""

import time
from typing import Any
from dataclasses import dataclass, field

from l3_assembly.events.payload_events import FrozenPayload

@dataclass
class SharedLoopState:
    """State blackboard for asynchronous tasks."""
    
    frozen: FrozenPayload | None = None
    payload_dict: dict[str, Any] | None = None
    last_payload_time: float = 0.0
    
    # Trackers for diagnostics
    total_computations: int = 0
    failed_computations: int = 0
    current_compute_interval: float = 1.0
    snapshot_version_iv_probe: dict[str, Any] = field(default_factory=dict)

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

    @property
    def is_running(self) -> bool:
        """Check if we have recent computations."""
        return self.last_payload_time > 0
    
    def get_diagnostics(self) -> dict[str, Any]:
        """Return agent runner diagnostics."""
        age = time.monotonic() - self.last_payload_time if self.last_payload_time else None
        total = self.total_computations + self.failed_computations
        return {
            "total_computations": self.total_computations,
            "failed_computations": self.failed_computations,
            "success_rate": (self.total_computations / total * 100) if total > 0 else 100.0,
            "last_update_age_seconds": age,
            "is_running": self.is_running,
            "snapshot_version_iv_probe": self.snapshot_version_iv_probe,
        }

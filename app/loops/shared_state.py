"""Shared state between asynchronous loops.

Decouples the compute loop (which writes state) from the broadcast
and housekeeping loops (which read state).
"""

import asyncio
import time
from datetime import datetime, timezone
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


@dataclass(frozen=True)
class LiveSpotSnapshot:
    """Latest live SPY spot event published by L0."""

    spot: float
    version: int
    data_timestamp: str


@dataclass
class SharedLoopState:
    """State blackboard for asynchronous tasks."""
    
    frozen: FrozenPayload | None = None
    payload_dict: dict[str, Any] | None = None
    payload_epoch: int = 0
    latest_live_spot: LiveSpotSnapshot | None = None
    latest_quote_lane_telemetry: dict[str, Any] | None = None
    latest_l1_snapshot: Any | None = None
    latest_active_options_input: ActiveOptionsInputSnapshot | None = None
    fatal_runtime_error: dict[str, Any] | None = None
    last_payload_time: float = 0.0
    last_active_options_input_time: float = 0.0
    _payload_update_event: asyncio.Event | None = field(default=None, init=False, repr=False)
    
    # Trackers for diagnostics
    total_computations: int = 0
    failed_computations: int = 0
    spot_updates: int = 0
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
        del spot
        reconciled = self._overlay_live_spot(frozen)
        reconciled = self._overlay_quote_lane_telemetry(reconciled)
        self._remember_live_spot(reconciled)
        self.frozen = reconciled
        self.payload_dict = reconciled.to_dict()
        self.last_payload_time = time.monotonic()
        self.payload_epoch += 1
        self.total_computations += 1
        self._payload_event().set()

    def publish_live_spot(
        self,
        *,
        spot: float,
        version: int,
        data_timestamp: str,
    ) -> None:
        """Overlay a live SPY spot tick onto the current payload without recompute."""
        live_spot = LiveSpotSnapshot(
            spot=float(spot),
            version=int(version),
            data_timestamp=str(data_timestamp),
        )
        self.latest_live_spot = live_spot
        if self.frozen is None:
            return
        if self.frozen.version >= live_spot.version and self.frozen.spot == live_spot.spot:
            return
        self.frozen = self.frozen.with_live_spot(
            spot=live_spot.spot,
            version=live_spot.version,
            data_timestamp=live_spot.data_timestamp,
            broadcast_timestamp=datetime.now(timezone.utc).isoformat(),
            quote_lane=self._quote_lane_telemetry(live_spot),
        )
        self.payload_dict = self.frozen.to_dict()
        self.last_payload_time = time.monotonic()
        self.payload_epoch += 1
        self.spot_updates += 1
        self._payload_event().set()

    def publish_quote_lane_telemetry(self, quote_lane: dict[str, Any]) -> None:
        """Overlay fresh quote-lane cadence telemetry without touching spot/version."""
        telemetry = self._source_quote_lane_telemetry(quote_lane)
        self.latest_quote_lane_telemetry = telemetry
        if self.frozen is None:
            return
        self.frozen = self.frozen.with_governor_telemetry({"quote_lane": telemetry})
        self.payload_dict = self.frozen.to_dict()
        self.last_payload_time = time.monotonic()
        self.payload_epoch += 1
        self._payload_event().set()

    def _overlay_live_spot(self, frozen: FrozenPayload) -> FrozenPayload:
        live_spot = self.latest_live_spot
        if live_spot is None or frozen.version >= live_spot.version:
            return frozen
        return frozen.with_live_spot(
            spot=live_spot.spot,
            version=live_spot.version,
            data_timestamp=live_spot.data_timestamp,
            broadcast_timestamp=datetime.now(timezone.utc).isoformat(),
            quote_lane=self._quote_lane_telemetry(live_spot),
        )

    def _overlay_quote_lane_telemetry(self, frozen: FrozenPayload) -> FrozenPayload:
        telemetry = self.latest_quote_lane_telemetry
        if telemetry is None:
            return frozen
        return frozen.with_governor_telemetry({"quote_lane": telemetry})

    def _remember_live_spot(self, frozen: FrozenPayload) -> None:
        spot = getattr(frozen, "spot", None)
        version = int(getattr(frozen, "version", 0) or 0)
        data_timestamp = getattr(frozen, "data_timestamp", None)
        if not isinstance(spot, (int, float)) or float(spot) <= 0.0 or version <= 0:
            return
        if not isinstance(data_timestamp, str) or not data_timestamp:
            return
        self.latest_live_spot = LiveSpotSnapshot(
            spot=float(spot),
            version=version,
            data_timestamp=data_timestamp,
        )

    @staticmethod
    def _quote_lane_telemetry(live_spot: LiveSpotSnapshot) -> dict[str, Any]:
        return {
            "mode": "live_spot",
            "source_data_timestamp_utc": live_spot.data_timestamp,
            "wire_version": int(live_spot.version),
            "spot": float(live_spot.spot),
        }

    @staticmethod
    def _source_quote_lane_telemetry(quote_lane: dict[str, Any]) -> dict[str, Any]:
        telemetry = dict(quote_lane)
        telemetry["mode"] = "source_cadence"
        source_ts = telemetry.get("source_data_timestamp_utc")
        if not isinstance(source_ts, str) or not source_ts:
            raw_source_ts = telemetry.get("last_source_timestamp_utc")
            if isinstance(raw_source_ts, str) and raw_source_ts:
                telemetry["source_data_timestamp_utc"] = raw_source_ts
        return telemetry

    def _payload_event(self) -> asyncio.Event:
        if self._payload_update_event is None:
            self._payload_update_event = asyncio.Event()
        return self._payload_update_event

    def set_fatal_runtime_error(self, *, source: str, message: str) -> None:
        self.fatal_runtime_error = {
            "source": str(source),
            "message": str(message),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._payload_event().set()

    def raise_if_fatal(self) -> None:
        fatal = self.fatal_runtime_error
        if fatal is None:
            return
        raise RuntimeError(f"{fatal['source']}: {fatal['message']}")

    async def wait_for_payload_after(
        self,
        last_seen_epoch: int,
        *,
        timeout_sec: float | None,
    ) -> bool:
        event = self._payload_event()
        if self.payload_epoch > last_seen_epoch:
            if event.is_set():
                event.clear()
            return True

        if event.is_set():
            event.clear()
        try:
            if timeout_sec is None:
                await event.wait()
            else:
                await asyncio.wait_for(event.wait(), timeout=max(0.0, timeout_sec))
        except TimeoutError:
            return self.payload_epoch > last_seen_epoch
        finally:
            if self.payload_epoch > last_seen_epoch and event.is_set():
                event.clear()
        return self.payload_epoch > last_seen_epoch

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

    def _live_spot_diagnostics(self) -> dict[str, Any]:
        live_spot = self.latest_live_spot
        return {
            "version": int(live_spot.version) if live_spot else 0,
            "spot": float(live_spot.spot) if live_spot else 0.0,
            "data_timestamp": live_spot.data_timestamp if live_spot else None,
        }

    def _active_options_input_diagnostics(self) -> dict[str, Any]:
        active_options_input = self.latest_active_options_input
        chain_size = len(active_options_input.chain) if active_options_input is not None else 0
        input_age = (
            time.monotonic() - self.last_active_options_input_time
            if self.last_active_options_input_time
            else None
        )
        return {
            "updates": self.active_options_input_updates,
            "age_seconds": input_age,
            "valid": bool(active_options_input.valid) if active_options_input else False,
            "chain_size": chain_size,
            "source_version": int(active_options_input.source_version) if active_options_input else 0,
            "source_timestamp_utc": active_options_input.source_timestamp_utc if active_options_input else None,
            "invalid_reason": active_options_input.invalid_reason if active_options_input else "missing_input",
        }

    def _gpu_compute_audit_diagnostics(self) -> dict[str, Any]:
        return {
            "compute_ticks_seen": self.compute_ticks_seen,
            "duplicate_snapshot_skips": self.duplicate_snapshot_skips,
            "l1_compute_runs": self.l1_compute_runs,
            "last_snapshot_version": self.last_snapshot_version,
            "last_compute_id": self.last_compute_id,
            "last_gpu_task_id": self.last_gpu_task_id,
        }

    def get_diagnostics(self) -> dict[str, Any]:
        """Return agent runner diagnostics."""
        age = time.monotonic() - self.last_payload_time if self.last_payload_time else None
        total = self.total_computations + self.failed_computations
        success_rate = (self.total_computations / total * 100) if total > 0 else 100.0
        return {
            "total_computations": self.total_computations,
            "failed_computations": self.failed_computations,
            "spot_updates": self.spot_updates,
            "success_rate": success_rate,
            "last_update_age_seconds": age,
            "is_running": self.is_running,
            "fatal_runtime_error": self.fatal_runtime_error,
            "live_spot": self._live_spot_diagnostics(),
            "snapshot_version_iv_probe": self.snapshot_version_iv_probe,
            "active_options_input": self._active_options_input_diagnostics(),
            "gpu_compute_audit": self._gpu_compute_audit_diagnostics(),
        }

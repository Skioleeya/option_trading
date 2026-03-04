"""l3_assembly.reactor — L3AssemblyReactor.

Main orchestrator for the L3 Output Assembly Layer.

Replaces the combined logic of:
    - AppContainer._agent_runner_loop (assembly portion)
    - AppContainer._broadcast_loop (broadcast portion)

Design:
    L3AssemblyReactor is a pure assembler — it does NOT own the broadcast
    loop timer. The calling code (AppContainer or new runtime) still controls
    the tick cadence. This makes the reactor fully testable without asyncio.

Usage:
    reactor = L3AssemblyReactor()

    # In compute loop (replaces SnapshotBuilder.build())
    frozen = await reactor.tick(decision, snapshot, atm_decay, active_options)

    # Broadcast (replaces _broadcast_loop body)
    report = await reactor.governor.broadcast(
        payload=frozen,
        clients=ws_clients,
        payload_time=last_compute_time,
        compute_interval=compute_interval,
    )

    # Historical query (replaces historical_store.get_latest())
    history = await reactor.store.get_warm_latest(50)

    # Backward-compat (replaces SnapshotBuilder.build() return value)
    legacy_dict = frozen.to_dict()
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from l3_assembly.events.payload_events import FrozenPayload
from l3_assembly.assembly.payload_assembler import PayloadAssemblerV2
from l3_assembly.assembly.delta_encoder import FieldDeltaEncoder
from l3_assembly.broadcast.broadcast_governor import BroadcastGovernor
from l3_assembly.storage.timeseries_store import TimeSeriesStoreV2
from l3_assembly.observability.l3_instrumentation import L3Instrumentation

logger = logging.getLogger(__name__)


class L3AssemblyReactor:
    """L3 Output Assembly Reactor — main orchestrator.

    Args:
        redis:                  Async Redis client (None = Warm tier disabled).
        full_snapshot_interval: Seconds between forced full WS snapshots (default 30s).
        max_hot:                Hot ring buffer capacity (default 7200 = 2h at 1Hz).
        shadow_mode:            If True, log numeric diffs vs legacy SnapshotBuilder.
    """

    def __init__(
        self,
        redis: Any = None,
        full_snapshot_interval: float = 30.0,
        max_hot: int = 7200,
        shadow_mode: bool = False,
    ) -> None:
        self.assembler = PayloadAssemblerV2()
        self.encoder = FieldDeltaEncoder(full_snapshot_interval)
        self.governor = BroadcastGovernor(encoder=self.encoder)
        self.store = TimeSeriesStoreV2(max_hot=max_hot, redis=redis)
        self.instrumentation = L3Instrumentation()
        self.shadow_mode = shadow_mode

        self._total_ticks = 0
        self._failed_ticks = 0

    async def tick(
        self,
        decision: Any,
        snapshot: Any,
        atm_decay: dict[str, Any] | None = None,
        active_options: Any = None,
    ) -> FrozenPayload:
        """Single compute tick: assemble + store FrozenPayload.

        This is a DROP-IN replacement for SnapshotBuilder.build().

        Args:
            decision:       L2 DecisionOutput or None (returns zero-state).
            snapshot:       L1 EnrichedSnapshot or legacy dict snapshot.
            atm_decay:      ATM decay tracker payload (pass-through).
            active_options: Pre-computed active options from background loop.

        Returns:
            FrozenPayload (immutable). Call .to_dict() for legacy wire format.
        """
        start = time.monotonic()
        self._total_ticks += 1

        try:
            spot = self._extract_spot(snapshot)

            with self.instrumentation.span_assemble(spot=spot):
                payload = await asyncio.to_thread(
                    self.assembler.assemble,
                    decision,
                    snapshot,
                    atm_decay,
                    active_options,
                )

            with self.instrumentation.span_timeseries():
                await self.store.write(payload)

            assemble_ms = (time.monotonic() - start) * 1000
            self.instrumentation.record_assembly_latency(assemble_ms)
            self.instrumentation.set_hot_size(self.store.hot_size())

            if self.shadow_mode and decision is not None:
                self._shadow_compare(payload, decision, snapshot)

            return payload

        except Exception as exc:
            self._failed_ticks += 1
            logger.exception(f"[L3 Reactor] tick failed (total_failures={self._failed_ticks}): {exc}")
            # Return a safe neutral payload so broadcast loop never stalls
            return self._safe_neutral_payload(snapshot)

    def get_diagnostics(self) -> dict[str, Any]:
        """Return L3 layer health diagnostics for /debug/persistence_status."""
        store_diag = self.store.get_diagnostics()
        return {
            "l3_reactor": {
                "total_ticks": self._total_ticks,
                "failed_ticks": self._failed_ticks,
                "success_rate": (
                    (self._total_ticks - self._failed_ticks) / self._total_ticks * 100
                    if self._total_ticks > 0 else 100.0
                ),
                "delta_ratio": f"{self.encoder.delta_ratio:.1%}",
            },
            "l3_store": store_diag,
        }

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _extract_spot(snapshot: Any) -> float:
        """Extract spot price from either typed EnrichedSnapshot or dict."""
        if hasattr(snapshot, "spot"):
            return float(snapshot.spot or 0.0)
        if isinstance(snapshot, dict):
            return float(snapshot.get("spot", 0.0) or 0.0)
        return 0.0

    @staticmethod
    def _safe_neutral_payload(snapshot: Any) -> FrozenPayload:
        """Return a minimal valid FrozenPayload for error recovery."""
        from l3_assembly.events.payload_events import (
            UIState, SignalData, FrozenPayload
        )
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        spot = L3AssemblyReactor._extract_spot(snapshot)
        return FrozenPayload(
            data_timestamp=now,
            broadcast_timestamp=now,
            spot=spot,
            version=0,
            drift_ms=0.0,
            drift_warning=False,
            signal=SignalData.neutral(),
            ui_state=UIState.zero_state(),
            atm=None,
        )

    def _shadow_compare(
        self,
        l3_payload: FrozenPayload,
        decision: Any,
        snapshot: Any,
    ) -> None:
        """Compare L3 output with legacy SnapshotBuilder (shadow mode)."""
        try:
            from app.services.system.snapshot_builder import SnapshotBuilder
            legacy = SnapshotBuilder.build(snapshot, decision, None)
            l3_spot = l3_payload.spot
            legacy_spot = legacy.get("spot", 0.0)
            if abs((l3_spot or 0) - (legacy_spot or 0)) > 0.01:
                logger.warning(
                    f"[L3 Shadow] spot mismatch: L3={l3_spot}, legacy={legacy_spot}"
                )
        except Exception as exc:
            logger.debug(f"[L3 Shadow] compare failed: {exc}")

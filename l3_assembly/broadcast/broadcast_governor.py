"""l3_assembly.broadcast.broadcast_governor — BroadcastGovernor.

1Hz rate-limited broadcaster extracted from AppContainer._broadcast_loop.

Responsibilities:
    - Stamps broadcast heartbeat timestamp on every payload
    - Determines is_stale based on payload age vs compute interval
    - Calls FieldDeltaEncoder to produce full or delta message
    - Serializes to JSON and fans out to all WebSocket clients
    - Returns BroadcastReport with per-cycle diagnostics

Design:
    BroadcastGovernor is stateless with respect to client management.
    It receives the client set from the AppContainer (or L3AssemblyReactor).
    Client set mutation (register/unregister) is handled externally.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from l3_assembly.events.payload_events import FrozenPayload
from l3_assembly.events.delta_events import DeltaPayload, DeltaType
from l3_assembly.assembly.delta_encoder import FieldDeltaEncoder

logger = logging.getLogger(__name__)


@dataclass
class BroadcastReport:
    """Diagnostics from one BroadcastGovernor cycle."""
    client_count: int
    message_type: str        # "full" | "delta" | "skipped"
    payload_age_ms: float    # age of payload at broadcast time
    is_stale: bool
    serialized_bytes: int
    delta_ratio: float
    broadcast_latency_ms: float
    failed_clients: int


class BroadcastGovernor:
    """1Hz rate-limiter and broadcaster.

    Usage:
        governor = BroadcastGovernor(encoder=FieldDeltaEncoder())

        # In broadcast loop:
        report = await governor.broadcast(
            payload=frozen_payload,
            clients=ws_clients,
            payload_time=last_payload_time,
            compute_interval=current_compute_interval,
        )
    """

    def __init__(
        self,
        encoder: FieldDeltaEncoder | None = None,
        full_snapshot_interval: float = 30.0,
    ) -> None:
        self._encoder = encoder or FieldDeltaEncoder(full_snapshot_interval)

    async def broadcast(
        self,
        payload: FrozenPayload,
        clients: set,
        payload_time: float = 0.0,
        compute_interval: float = 1.0,
    ) -> BroadcastReport:
        """Broadcast payload to all WebSocket clients.

        Args:
            payload:          Current FrozenPayload from runner loop.
            clients:          Set of connected WebSocket objects.
            payload_time:     monotonic time when payload was computed.
            compute_interval: Current compute cadence (for is_stale threshold).

        Returns:
            BroadcastReport with per-cycle diagnostics.
        """
        start = time.monotonic()

        # ── 1. Stamp broadcast fields ──────────────────────────────────────
        heartbeat = datetime.now(timezone.utc).isoformat()
        payload_age = (time.monotonic() - payload_time) if payload_time > 0 else 0.0
        stale_threshold = compute_interval * 2.5
        is_stale = payload_age > stale_threshold

        # ── 2. Encode (full or delta) ──────────────────────────────────────
        delta_msg = self._encoder.encode(
            current=payload,
            heartbeat_timestamp=heartbeat,
            is_stale=is_stale,
        )
        msg_dict = delta_msg.to_dict()

        # ── 3. Serialize ───────────────────────────────────────────────────
        serialized = json.dumps(msg_dict, default=str)
        byte_count = len(serialized.encode("utf-8"))

        # ── 4. Fan-out broadcast ───────────────────────────────────────────
        client_count, failed = await self._fanout(clients, serialized)

        latency_ms = (time.monotonic() - start) * 1000

        logger.debug(
            f"[L3 Governor] {delta_msg.type.value}: "
            f"clients={client_count}, age={payload_age*1000:.0f}ms, "
            f"bytes={byte_count}, lat={latency_ms:.1f}ms, "
            f"delta_ratio={self._encoder.delta_ratio:.2%}"
        )

        return BroadcastReport(
            client_count=client_count,
            message_type=delta_msg.type.value,
            payload_age_ms=payload_age * 1000,
            is_stale=is_stale,
            serialized_bytes=byte_count,
            delta_ratio=self._encoder.delta_ratio,
            broadcast_latency_ms=latency_ms,
            failed_clients=failed,
        )

    @staticmethod
    async def _fanout(clients: set, message: str) -> tuple[int, int]:
        """Send message to all clients, removing disconnected ones.

        Returns:
            (success_count, fail_count)
        """
        if not clients:
            return 0, 0

        disconnected: set = set()
        tasks = []

        for ws in clients:
            tasks.append(_safe_send(ws, message, disconnected))

        await asyncio.gather(*tasks, return_exceptions=True)

        if disconnected:
            clients -= disconnected

        return len(clients), len(disconnected)

    async def broadcast_init(self, payload: FrozenPayload, ws: Any) -> None:
        """Send initial full snapshot to a newly connected WebSocket client."""
        heartbeat = datetime.now(timezone.utc).isoformat()
        stamped = payload.with_broadcast_fields(
            heartbeat_timestamp=heartbeat,
            is_stale=False,
            msg_type="dashboard_init",
        )
        msg = {**stamped.to_dict(), "type": DeltaType.INIT.value}
        serialized = json.dumps(msg, default=str)
        try:
            await ws.send_text(serialized)
        except Exception as exc:
            logger.warning(f"[L3 Governor] Failed to send init to client: {exc}")


async def _safe_send(ws: Any, message: str, disconnected: set) -> None:
    """Send message to one WS client, adding to disconnected set on failure."""
    try:
        await ws.send_text(message)
    except Exception as exc:
        logger.debug(f"[L3 Governor] Client disconnected: {exc}")
        disconnected.add(ws)

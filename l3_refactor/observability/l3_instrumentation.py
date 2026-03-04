"""l3_refactor.observability.l3_instrumentation — L3 OTel + Prometheus.

Follows the same no-op fallback design as L0/L1/L2 instrumentation:
if opentelemetry or prometheus_client are not installed, all calls
are silently no-ops — never raises, never blocks the hot path.

OTel Spans:
    l3.assemble       — PayloadAssemblerV2.assemble()
    l3.delta_encode   — FieldDeltaEncoder.encode()
    l3.broadcast      — BroadcastGovernor.broadcast() per cycle
    l3.timeseries     — TimeSeriesStoreV2.write()

Prometheus Metrics:
    l3_assembly_latency_ms    — Histogram: assemble() latency
    l3_broadcast_latency_ms   — Histogram: broadcast cycle latency
    l3_broadcast_clients      — Gauge: connected WS clients
    l3_delta_ratio            — Gauge: fraction of delta (vs full) messages
    l3_timeseries_hot_size    — Gauge: entries in hot ring buffer
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger(__name__)


# ── OTel probe ─────────────────────────────────────────────────────────────

try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.trace import Span, Status, StatusCode
    _OTEL_AVAILABLE = True
    _tracer = otel_trace.get_tracer("l3_refactor", "3.1.0")
    logger.info("[L3 Instrumentation] OpenTelemetry detected — spans enabled")
except ImportError:
    _OTEL_AVAILABLE = False
    logger.debug("[L3 Instrumentation] OpenTelemetry not available — no-op spans")


# ── Prometheus probe ────────────────────────────────────────────────────────

try:
    from prometheus_client import Histogram, Gauge
    _assembly_latency = Histogram(
        "l3_assembly_latency_ms", "PayloadAssemblerV2.assemble() latency",
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0],
    )
    _broadcast_latency = Histogram(
        "l3_broadcast_latency_ms", "BroadcastGovernor.broadcast() latency",
        buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0],
    )
    _broadcast_clients = Gauge("l3_broadcast_clients", "Connected WS clients")
    _delta_ratio = Gauge("l3_delta_ratio", "Fraction of delta vs full messages")
    _hot_size = Gauge("l3_timeseries_hot_size", "TimeSeriesStore hot-layer entries")
    _PROMETHEUS_AVAILABLE = True
    logger.info("[L3 Instrumentation] Prometheus detected — metrics enabled")
except ImportError:
    _PROMETHEUS_AVAILABLE = False
    logger.debug("[L3 Instrumentation] Prometheus not available — no-op metrics")


class L3Instrumentation:
    """OTel + Prometheus instrumentation for L3 layer.

    All methods are safe to call even if dependencies are absent.
    """

    @staticmethod
    @contextmanager
    def span_assemble(spot: float) -> Generator[Any, None, None]:
        """Context manager wrapping PayloadAssemblerV2.assemble()."""
        if _OTEL_AVAILABLE:
            with _tracer.start_as_current_span("l3.assemble") as span:
                span.set_attribute("spot", spot)
                yield span
        else:
            yield None

    @staticmethod
    @contextmanager
    def span_delta_encode() -> Generator[Any, None, None]:
        """Context manager wrapping FieldDeltaEncoder.encode()."""
        if _OTEL_AVAILABLE:
            with _tracer.start_as_current_span("l3.delta_encode") as span:
                yield span
        else:
            yield None

    @staticmethod
    @contextmanager
    def span_broadcast(client_count: int) -> Generator[Any, None, None]:
        """Context manager wrapping BroadcastGovernor.broadcast()."""
        if _OTEL_AVAILABLE:
            with _tracer.start_as_current_span("l3.broadcast") as span:
                span.set_attribute("client_count", client_count)
                yield span
        else:
            yield None

    @staticmethod
    @contextmanager
    def span_timeseries() -> Generator[Any, None, None]:
        """Context manager wrapping TimeSeriesStoreV2.write()."""
        if _OTEL_AVAILABLE:
            with _tracer.start_as_current_span("l3.timeseries") as span:
                yield span
        else:
            yield None

    @staticmethod
    def record_assembly_latency(ms: float) -> None:
        if _PROMETHEUS_AVAILABLE:
            _assembly_latency.observe(ms)

    @staticmethod
    def record_broadcast_latency(ms: float) -> None:
        if _PROMETHEUS_AVAILABLE:
            _broadcast_latency.observe(ms)

    @staticmethod
    def set_client_count(n: int) -> None:
        if _PROMETHEUS_AVAILABLE:
            _broadcast_clients.set(n)

    @staticmethod
    def set_delta_ratio(ratio: float) -> None:
        if _PROMETHEUS_AVAILABLE:
            _delta_ratio.set(ratio)

    @staticmethod
    def set_hot_size(n: int) -> None:
        if _PROMETHEUS_AVAILABLE:
            _hot_size.set(n)

"""L1 Observability — OTel spans + Prometheus metrics with no-op fallback.

When opentelemetry-api / prometheus-client are not installed, all
instrumentation calls silently become no-ops. This matches the L0 pattern
established in l0_refactor/observability/.

OTel span hierarchy:
    l1.compute (root)
     ├── l1.iv_resolution
     ├── l1.greeks_kernel
     ├── l1.aggregation
     └── l1.microstructure

Prometheus metrics (all with prefix `l1_`):
    l1_greeks_latency_seconds    — Histogram
    l1_compute_tier_total        — Counter (labels: tier=gpu|numba|numpy)
    l1_iv_source_total           — Counter (labels: source=ws|rest|chain|sabr|missing)
    l1_contracts_computed_total  — Counter
    l1_nan_count_total           — Counter
    l1_chain_size                — Gauge
"""

from __future__ import annotations

import contextlib
import logging
import time
from contextlib import contextmanager
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)

# ── OTel import ────────────────────────────────────────────────────────────────
try:
    from opentelemetry import trace  # type: ignore
    from opentelemetry.trace import Span, StatusCode  # type: ignore
    _OTEL_AVAILABLE = True
    _tracer = trace.get_tracer("l1_refactor", schema_url="https://opentelemetry.io/schemas/1.11.0")
    logger.info("[L1Instrumentation] OpenTelemetry active.")
except ImportError:
    _OTEL_AVAILABLE = False
    _tracer = None
    logger.debug("[L1Instrumentation] OpenTelemetry not available — no-op mode.")

# ── Prometheus import ─────────────────────────────────────────────────────────
try:
    from prometheus_client import Counter, Histogram, Gauge, REGISTRY  # type: ignore
    _PROM_AVAILABLE = True
    _hist_greeks_latency = Histogram(
        "l1_greeks_latency_seconds",
        "L1 Greeks computation latency",
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 1.0],
    )
    _ctr_compute_tier = Counter(
        "l1_compute_tier_total",
        "L1 compute tier selected",
        labelnames=["tier"],
    )
    _ctr_iv_source = Counter(
        "l1_iv_source_total",
        "L1 IV resolution source",
        labelnames=["source"],
    )
    _ctr_contracts = Counter("l1_contracts_computed_total", "Contracts with valid Greeks computed")
    _ctr_nan = Counter("l1_nan_count_total", "NaN values detected in Greeks output")
    _gauge_chain_size = Gauge("l1_chain_size", "Current option chain size")
    logger.info("[L1Instrumentation] Prometheus metrics registered.")
except (ImportError, Exception):
    _PROM_AVAILABLE = False
    logger.debug("[L1Instrumentation] Prometheus not available — no-op mode.")


class _NoOpSpan:
    """No-op span for environments without OpenTelemetry."""
    def set_attribute(self, key: str, value: Any) -> None: ...
    def set_status(self, *args: Any, **kwargs: Any) -> None: ...
    def record_exception(self, exc: Exception) -> None: ...
    def __enter__(self): return self
    def __exit__(self, *args): ...


class L1Instrumentation:
    """L1 layer observability facade.

    All methods are safe to call even when OTel / Prometheus are absent.

    Usage::

        inst = L1Instrumentation()
        with inst.span_greeks_kernel() as span:
            span.set_attribute("compute_tier", "gpu")
            span.set_attribute("chain_size", 200)
            matrix = router.compute(...)
        inst.record_compute_tier("gpu")
        inst.record_greeks_latency(elapsed_ms / 1000)
    """

    def __init__(self) -> None:
        self._has_otel = _OTEL_AVAILABLE
        self._has_prom = _PROM_AVAILABLE

    # ── OTel span context managers ─────────────────────────────────────────────

    @contextmanager
    def span_compute(self) -> Generator:
        """Root L1 compute span."""
        yield from self._maybe_span("l1.compute")

    @contextmanager
    def span_iv_resolution(self) -> Generator:
        """IV resolution span."""
        yield from self._maybe_span("l1.iv_resolution")

    @contextmanager
    def span_greeks_kernel(self) -> Generator:
        """Greeks kernel span."""
        yield from self._maybe_span("l1.greeks_kernel")

    @contextmanager
    def span_aggregation(self) -> Generator:
        """StreamingAggregator span."""
        yield from self._maybe_span("l1.aggregation")

    @contextmanager
    def span_microstructure(self) -> Generator:
        """Microstructure core span."""
        yield from self._maybe_span("l1.microstructure")

    # ── Prometheus metrics ────────────────────────────────────────────────────

    def record_greeks_latency(self, seconds: float) -> None:
        if self._has_prom:
            try:
                _hist_greeks_latency.observe(seconds)
            except Exception:
                pass

    def record_compute_tier(self, tier: str) -> None:
        """Record which compute tier was selected (gpu / numba / numpy)."""
        if self._has_prom:
            try:
                _ctr_compute_tier.labels(tier=tier).inc()
            except Exception:
                pass

    def record_iv_source(self, source: str, count: int = 1) -> None:
        """Record IV resolution source distribution."""
        if self._has_prom:
            try:
                _ctr_iv_source.labels(source=source).inc(count)
            except Exception:
                pass

    def record_contracts_computed(self, count: int) -> None:
        if self._has_prom:
            try:
                _ctr_contracts.inc(count)
            except Exception:
                pass

    def record_nan_count(self, count: int) -> None:
        if self._has_prom and count > 0:
            try:
                _ctr_nan.inc(count)
            except Exception:
                pass

    def set_chain_size(self, size: int) -> None:
        if self._has_prom:
            try:
                _gauge_chain_size.set(size)
            except Exception:
                pass

    # ── Private ────────────────────────────────────────────────────────────────

    def _maybe_span(self, name: str) -> Generator:
        if self._has_otel and _tracer is not None:
            with _tracer.start_as_current_span(name) as span:
                yield span
        else:
            yield _NoOpSpan()

"""l2_refactor.observability.l2_instrumentation — OTel spans + Prometheus metrics.

Structure mirrors l1_refactor/observability/l1_instrumentation.py.
No-op fallback when OTel/Prometheus are not installed.

Spans:
    l2.feature_store.compute
    l2.signal.{name}
    l2.fusion
    l2.guard_rails
    l2.decision

Prometheus:
    l2_feature_extraction_latency_ms (Histogram)
    l2_fusion_latency_ms             (Histogram)
    l2_decision_confidence           (Histogram)
    l2_guard_triggers_total          (Counter, label: rule_name)
    l2_signal_direction_total        (Counter, labels: signal, direction)
    l2_shadow_mismatch_total         (Counter)
"""

from __future__ import annotations

import contextlib
import logging
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)

# ── OTel (optional) ──────────────────────────────────────────────────────────
try:
    from opentelemetry import trace as _otel_trace
    _tracer = _otel_trace.get_tracer("l2_refactor")
    _HAS_OTEL = True
except ImportError:
    _HAS_OTEL = False
    _tracer = None  # type: ignore

# ── Prometheus (optional) ─────────────────────────────────────────────────────
try:
    from prometheus_client import Counter, Histogram
    _feature_latency = Histogram(
        "l2_feature_extraction_latency_ms",
        "Feature extraction latency in ms",
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
    )
    _fusion_latency = Histogram(
        "l2_fusion_latency_ms",
        "Fusion engine latency in ms",
        buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0],
    )
    _decision_confidence = Histogram(
        "l2_decision_confidence",
        "Final decision confidence distribution",
        buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    )
    _guard_triggers = Counter(
        "l2_guard_triggers_total",
        "Guard rules triggered",
        ["rule_name"],
    )
    _signal_direction = Counter(
        "l2_signal_direction_total",
        "Signal direction counts",
        ["signal_name", "direction"],
    )
    _shadow_mismatch = Counter(
        "l2_shadow_mismatch_total",
        "Decisions where attention != rule fusion",
    )
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False


class _NoOpSpan:
    def set_attribute(self, *args, **kwargs) -> None: pass
    def __enter__(self): return self
    def __exit__(self, *args): pass


class L2Instrumentation:
    """OTel + Prometheus instrumentation for L2 Decision Layer."""

    @contextmanager
    def span_feature_store(self) -> Generator[_NoOpSpan, None, None]:
        if _HAS_OTEL and _tracer:
            with _tracer.start_as_current_span("l2.feature_store.compute") as span:
                yield span  # type: ignore
        else:
            yield _NoOpSpan()

    @contextmanager
    def span_signal(self, name: str) -> Generator[_NoOpSpan, None, None]:
        if _HAS_OTEL and _tracer:
            with _tracer.start_as_current_span(f"l2.signal.{name}") as span:
                yield span  # type: ignore
        else:
            yield _NoOpSpan()

    @contextmanager
    def span_fusion(self) -> Generator[_NoOpSpan, None, None]:
        if _HAS_OTEL and _tracer:
            with _tracer.start_as_current_span("l2.fusion") as span:
                yield span  # type: ignore
        else:
            yield _NoOpSpan()

    @contextmanager
    def span_guard_rails(self) -> Generator[_NoOpSpan, None, None]:
        if _HAS_OTEL and _tracer:
            with _tracer.start_as_current_span("l2.guard_rails") as span:
                yield span  # type: ignore
        else:
            yield _NoOpSpan()

    def record_feature_latency(self, latency_ms: float) -> None:
        if _HAS_PROMETHEUS:
            with contextlib.suppress(Exception):
                _feature_latency.observe(latency_ms)

    def record_fusion_latency(self, latency_ms: float) -> None:
        if _HAS_PROMETHEUS:
            with contextlib.suppress(Exception):
                _fusion_latency.observe(latency_ms)

    def record_decision_confidence(self, confidence: float) -> None:
        if _HAS_PROMETHEUS:
            with contextlib.suppress(Exception):
                _decision_confidence.observe(confidence)

    def record_guard_trigger(self, rule_name: str) -> None:
        if _HAS_PROMETHEUS:
            with contextlib.suppress(Exception):
                _guard_triggers.labels(rule_name=rule_name).inc()

    def record_signal_direction(self, signal_name: str, direction: str) -> None:
        if _HAS_PROMETHEUS:
            with contextlib.suppress(Exception):
                _signal_direction.labels(signal_name=signal_name, direction=direction).inc()

    def record_shadow_mismatch(self) -> None:
        if _HAS_PROMETHEUS:
            with contextlib.suppress(Exception):
                _shadow_mismatch.inc()

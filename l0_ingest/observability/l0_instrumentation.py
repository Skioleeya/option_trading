"""
L0 可观测性桩 — OTel + Prometheus

设计：无 OTel 依赖时 graceful fallback（不崩溃）。
所有 span 和 counter 操作在无依赖时为无操作（no-op）。

用法:
    from l0_ingest.observability import trace_ingest

    @trace_ingest
    def my_ingest_function(...):
        ...
"""
from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, TypeVar, Optional

logger = logging.getLogger(__name__)

# ─── 尝试导入 OTel（可选依赖） ───────────────────────────────────────
try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider
    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False
    otel_trace = None  # type: ignore[assignment]
    TracerProvider = None  # type: ignore[assignment]

# ─── 尝试导入 Prometheus（可选依赖） ────────────────────────────────
try:
    from prometheus_client import Counter, Histogram
    _PROM_AVAILABLE = True
except ImportError:
    _PROM_AVAILABLE = False
    Counter = None    # type: ignore[assignment]
    Histogram = None  # type: ignore[assignment]


F = TypeVar("F", bound=Callable[..., Any])


# ─────────────────────────────────────────────────────────────────────
#  Prometheus 桩
# ─────────────────────────────────────────────────────────────────────
class _NoOpCounter:
    def inc(self, amount: float = 1, **kwargs: Any) -> None: pass
    def labels(self, **kwargs: Any) -> "_NoOpCounter": return self


class _NoOpHistogram:
    def observe(self, amount: float, **kwargs: Any) -> None: pass
    def labels(self, **kwargs: Any) -> "_NoOpHistogram": return self
    def time(self) -> Any:
        import contextlib
        return contextlib.nullcontext()


def _make_counter(name: str, doc: str, labels: Optional[list] = None) -> Any:
    if _PROM_AVAILABLE and Counter:
        try:
            return Counter(name, doc, labels or [])
        except Exception:
            pass
    return _NoOpCounter()


def _make_histogram(name: str, doc: str, labels: Optional[list] = None) -> Any:
    if _PROM_AVAILABLE and Histogram:
        try:
            return Histogram(name, doc, labels or [])
        except Exception:
            pass
    return _NoOpHistogram()


# ─────────────────────────────────────────────────────────────────────
#  指标注册
# ─────────────────────────────────────────────────────────────────────
class L0Instrumentation:
    """L0 层指标集中管理"""

    ingest_events_total   = _make_counter(
        "l0_ingest_events_total", "Total L0 ingest events", ["event_type", "symbol"]
    )
    sanitize_pass_total   = _make_counter(
        "l0_sanitize_pass_total", "Sanitize pipeline pass count", ["symbol"]
    )
    sanitize_drop_total   = _make_counter(
        "l0_sanitize_drop_total", "Sanitize pipeline drop count", ["reason"]
    )
    breaker_trip_total    = _make_counter(
        "l0_breaker_trip_total", "Circuit breaker trips", ["symbol", "reason"]
    )
    store_commit_total    = _make_counter(
        "l0_store_commit_total", "MVCC store commits", ["source"]
    )
    ingest_latency_ms     = _make_histogram(
        "l0_ingest_latency_ms", "Ingest end-to-end latency (ms)"
    )
    sanitize_latency_ms   = _make_histogram(
        "l0_sanitize_latency_ms", "Sanitize pipeline latency (ms)"
    )


# ─────────────────────────────────────────────────────────────────────
#  装饰器工厂
# ─────────────────────────────────────────────────────────────────────
def _make_trace_decorator(stage: str) -> Callable[[F], F]:
    """创建追踪装饰器（支持 OTel，无 OTel 时退回到日志计时）"""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            t0 = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                raise
            finally:
                elapsed_ms = (time.perf_counter() - t0) * 1000
                if elapsed_ms > 50:  # 超过 50ms 才记录，减少噪音
                    logger.debug(f"[L0:{stage}] {func.__name__} took {elapsed_ms:.1f}ms")
        return wrapper  # type: ignore[return-value]
    return decorator


trace_ingest   = _make_trace_decorator("ingest")
trace_sanitize = _make_trace_decorator("sanitize")
trace_store    = _make_trace_decorator("store")

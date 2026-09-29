"""OpenAPI endpoint/bootstrap helpers for L0 runtime wiring."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .quote_runtime import L0QuoteRuntime
from .quote_runtime.helpers import build_openapi_endpoint_profiles, longport_config_kwargs

logger = logging.getLogger(__name__)


def _build_openapi_endpoint_profiles(cfg: Any) -> list[dict[str, str]]:
    return build_openapi_endpoint_profiles(cfg)


def _longport_config_kwargs(cfg: Any) -> dict[str, Any]:
    return longport_config_kwargs(cfg)


def _runtime_diagnostics(runtime: L0QuoteRuntime) -> dict[str, Any]:
    try:
        data = runtime.diagnostics()
        if isinstance(data, dict):
            return data
    except Exception as exc:  # pragma: no cover
        return {"diagnostics_error": str(exc)}
    return {}


def _probe_quote_last_done(row: Any) -> float:
    raw = getattr(row, "last_done", None)
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"probe quote row has invalid last_done: {raw!r}") from exc
    if value <= 0.0:
        raise RuntimeError(f"probe quote row has non-positive last_done: {value}")
    return value


def _resolve_retry_policy(retry_attempts: int, retry_base_sec: float) -> tuple[int, float]:
    """Validate the retry policy declared in config. No implicit defaults: fail fast."""
    attempts = int(retry_attempts)
    if attempts < 1:
        raise RuntimeError(
            "longport_connect_retries must be >= 1 so startup probes the endpoint "
            f"at least once, got {retry_attempts!r}."
        )
    base_sec = float(retry_base_sec)
    if base_sec < 0.0:
        raise RuntimeError(
            f"longport_connect_retry_base_sec must be >= 0, got {retry_base_sec!r}."
        )
    return attempts, base_sec


async def _probe_quote_rows_with_retry(
    runtime: L0QuoteRuntime,
    probe_symbol: str,
    *,
    attempts: int,
    base_sec: float,
) -> list[Any]:
    """Call the REST quote endpoint, retrying only transient transport failures.

    A returned (possibly empty) row set is a data answer, not a transport fault, so it is
    never retried: contract violations must surface immediately. When every attempt fails
    the *original* transport exception is re-raised so the caller keeps reporting it verbatim.
    """
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await runtime.quote([probe_symbol])
        except Exception as exc:  # noqa: BLE001 - transport faults are retryable here
            last_exc = exc
            if attempt >= attempts:
                break
            delay_sec = base_sec * (2 ** (attempt - 1))
            logger.warning(
                "[OpenApiBootstrap] Startup connectivity probe attempt %d/%d failed: %s "
                "— retrying in %.2fs",
                attempt,
                attempts,
                exc,
                delay_sec,
            )
            await asyncio.sleep(delay_sec)
    if last_exc is None:  # pragma: no cover - unreachable: attempts >= 1 always sets it
        raise RuntimeError("startup connectivity probe produced no result and no error")
    raise last_exc


async def _startup_connectivity_probe(
    runtime: L0QuoteRuntime,
    *,
    strict_connectivity: bool,
    retry_attempts: int,
    retry_base_sec: float,
    probe_symbol: str = "SPY.US",
) -> float:
    if not strict_connectivity:
        raise RuntimeError(
            "strict_connectivity=false is forbidden by runtime policy. "
            "Startup must enforce hard-fail connectivity checks."
        )

    attempts, base_sec = _resolve_retry_policy(retry_attempts, retry_base_sec)

    try:
        rows = await _probe_quote_rows_with_retry(
            runtime,
            probe_symbol,
            attempts=attempts,
            base_sec=base_sec,
        )
    except Exception as exc:
        diagnostics = _runtime_diagnostics(runtime)
        profile = diagnostics.get("endpoint_profile")
        endpoint = diagnostics.get("endpoint_http_url")
        raise RuntimeError(
            "startup connectivity probe failed for quote runtime: "
            f"profile={profile} endpoint={endpoint} error={exc} attempts={attempts}"
        ) from exc
    if not rows:
        raise RuntimeError(
            "startup connectivity probe returned no rows: "
            f"symbol={probe_symbol}"
        )
    spot = _probe_quote_last_done(rows[0])
    diagnostics = _runtime_diagnostics(runtime)
    logger.info(
        "[OpenApiBootstrap] Startup connectivity probe passed: symbol=%s rows=%d spot=%.4f profile=%s endpoint=%s",
        probe_symbol,
        len(rows),
        spot,
        diagnostics.get("endpoint_profile"),
        diagnostics.get("endpoint_http_url"),
    )
    return spot

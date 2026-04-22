"""OpenAPI endpoint/bootstrap helpers for L0 runtime wiring."""

from __future__ import annotations

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


async def _startup_connectivity_probe(
    runtime: L0QuoteRuntime,
    *,
    strict_connectivity: bool,
    probe_symbol: str = "SPY.US",
) -> float:
    if not strict_connectivity:
        raise RuntimeError(
            "strict_connectivity=false is forbidden by runtime policy. "
            "Startup must enforce hard-fail connectivity checks."
        )

    try:
        rows = await runtime.quote([probe_symbol])
    except Exception as exc:
        diagnostics = _runtime_diagnostics(runtime)
        profile = diagnostics.get("endpoint_profile")
        endpoint = diagnostics.get("endpoint_http_url")
        raise RuntimeError(
            "startup connectivity probe failed for quote runtime: "
            f"profile={profile} endpoint={endpoint} error={exc}"
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

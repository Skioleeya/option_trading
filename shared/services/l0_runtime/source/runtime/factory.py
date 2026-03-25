"""Create source-layer runtime objects for the L0 V2 facade."""

from __future__ import annotations

from dataclasses import dataclass

from longport.openapi import Config

from shared.config import settings
from .openapi_bootstrap import (
    _build_openapi_endpoint_profiles,
    _longport_config_kwargs,
    _sync_openapi_env_aliases,
)
from .quote_runtime import L0QuoteRuntime, PythonQuoteRuntime, RustQuoteRuntime
from .rate_limiter import APIRateLimiter


@dataclass(frozen=True)
class RuntimeBundle:
    config: Config
    quote_runtime: L0QuoteRuntime
    rate_limiter: APIRateLimiter


def build_runtime_bundle() -> RuntimeBundle:
    endpoint_profiles = _build_openapi_endpoint_profiles(settings)
    _sync_openapi_env_aliases(settings)
    config = Config(**_longport_config_kwargs(settings))

    limiter = APIRateLimiter(
        rate=settings.longport_api_rate_limit,
        burst=settings.longport_api_burst,
        max_concurrent=settings.longport_api_max_concurrent,
        symbol_rate=settings.longport_steady_symbol_rate_per_min,
        symbol_burst=settings.longport_steady_symbol_burst,
        startup_symbol_rate=settings.longport_startup_symbol_rate_per_min,
        startup_symbol_burst=settings.longport_startup_symbol_burst,
        steady_symbol_rate=settings.longport_steady_symbol_rate_per_min,
        steady_symbol_burst=settings.longport_steady_symbol_burst,
    )

    runtime_mode = str(getattr(settings, "longport_runtime_mode", "rust_only")).strip().lower()
    if runtime_mode in {"python", "python_fallback"}:
        runtime: L0QuoteRuntime = PythonQuoteRuntime(config)
    else:
        runtime = RustQuoteRuntime(config, endpoint_profiles=endpoint_profiles)

    return RuntimeBundle(
        config=config,
        quote_runtime=runtime,
        rate_limiter=limiter,
    )

"""Create source-layer runtime objects for the L0 V2 facade."""

from __future__ import annotations

from dataclasses import dataclass

from longport.openapi import Config

from shared.config import settings
from .quote_runtime import L0QuoteRuntime, RustQuoteRuntime
from .rate_limiter import APIRateLimiter
from .sdk_bootstrap import (
    _build_openapi_endpoint_profiles,
    _longport_config_kwargs,
)
from ._native_quote_profile_support import build_gateway_config_native


@dataclass(frozen=True)
class RuntimeBundle:
    config: Config
    quote_runtime: L0QuoteRuntime
    rate_limiter: APIRateLimiter


def _build_rust_gateway_config(cfg: object) -> dict[str, object]:
    return build_gateway_config_native(
        app_key=str(getattr(cfg, "longport_app_key")),
        app_secret=str(getattr(cfg, "longport_app_secret")),
        access_token=str(getattr(cfg, "longport_access_token")),
        http_url=getattr(cfg, "longport_http_url", None),
        quote_ws_url=getattr(cfg, "longport_quote_ws_url", None),
        trade_ws_url=getattr(cfg, "longport_trade_ws_url", None),
        language=getattr(cfg, "longport_language", None),
        enable_overnight=bool(getattr(cfg, "longport_enable_overnight", False)),
    )


def build_runtime_bundle() -> RuntimeBundle:
    endpoint_profiles = _build_openapi_endpoint_profiles(settings)
    config = Config(**_longport_config_kwargs(settings))
    gateway_config = _build_rust_gateway_config(settings)
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
    runtime: L0QuoteRuntime = RustQuoteRuntime(
        config,
        endpoint_profiles=endpoint_profiles,
        gateway_config=gateway_config,
    )
    return RuntimeBundle(config=config, quote_runtime=runtime, rate_limiter=limiter)

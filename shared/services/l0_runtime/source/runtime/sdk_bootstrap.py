"""OpenAPI endpoint/bootstrap helpers for L0 runtime wiring."""

from __future__ import annotations

import logging
from typing import Any

from longport.openapi import Language

from ._native_quote_profile_support import (
    build_endpoint_profiles_native,
    build_gateway_config_native,
)
from .quote_runtime import L0QuoteRuntime

logger = logging.getLogger(__name__)

_DEFAULT_HTTP_URL = "https://openapi.longportapp.com"
_DEFAULT_QUOTE_WS_URL = "wss://openapi-quote.longportapp.com/v2"
_DEFAULT_TRADE_WS_URL = "wss://openapi-trade.longportapp.com/v2"

_LEGACY_HTTP_URL = "https://openapi.longbridge.com"
_LEGACY_QUOTE_WS_URL = "wss://openapi-quote.longbridge.com/v2"
_LEGACY_TRADE_WS_URL = "wss://openapi-trade.longbridge.com/v2"


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_language(value: Any) -> Language | None:
    if value is None:
        return None
    if isinstance(value, Language):
        return value
    text = _optional_text(value)
    if text is None:
        return None
    normalized = text.lower().replace("_", "-")
    mapping = {"en": Language.EN, "zh-cn": Language.ZH_CN, "zh-hk": Language.ZH_HK}
    resolved = mapping.get(normalized)
    if resolved is None:
        logger.warning(
            "[OpenApiBootstrap] Unsupported language '%s'; fallback to Language.EN",
            text,
        )
        return Language.EN
    return resolved


def _convert_gateway(value: str, src_host: str, dst_host: str) -> str:
    return value.replace(src_host, dst_host)


def _dedupe_endpoint_profiles(profiles: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for profile in profiles:
        key = (
            profile.get("http_url", ""),
            profile.get("quote_ws_url", ""),
            profile.get("trade_ws_url", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(profile)
    return out


def _build_openapi_endpoint_profiles(cfg: Any) -> list[dict[str, str]]:
    return build_endpoint_profiles_native(
        http_url=_optional_text(getattr(cfg, "longport_http_url", None)),
        quote_ws_url=_optional_text(getattr(cfg, "longport_quote_ws_url", None)),
        trade_ws_url=_optional_text(getattr(cfg, "longport_trade_ws_url", None)),
    )


def _longport_config_kwargs(cfg: Any) -> dict[str, Any]:
    gateway = build_gateway_config_native(
        app_key=str(getattr(cfg, "longport_app_key")),
        app_secret=str(getattr(cfg, "longport_app_secret")),
        access_token=str(getattr(cfg, "longport_access_token")),
        http_url=_optional_text(getattr(cfg, "longport_http_url", None)),
        quote_ws_url=_optional_text(getattr(cfg, "longport_quote_ws_url", None)),
        trade_ws_url=_optional_text(getattr(cfg, "longport_trade_ws_url", None)),
        language=_optional_text(getattr(cfg, "longport_language", None)),
        enable_overnight=bool(getattr(cfg, "longport_enable_overnight", False)),
    )
    return {
        "app_key": gateway["app_key"],
        "app_secret": gateway["app_secret"],
        "access_token": gateway["access_token"],
        "http_url": gateway["http_url"],
        "quote_ws_url": gateway["quote_ws_url"],
        "trade_ws_url": gateway["trade_ws_url"],
        "language": _resolve_language(gateway["language"]),
        "enable_overnight": gateway["enable_overnight"],
    }


def _runtime_diagnostics(runtime: L0QuoteRuntime) -> dict[str, Any]:
    try:
        data = runtime.diagnostics()
        if isinstance(data, dict):
            return data
    except Exception as exc:  # pragma: no cover
        return {"diagnostics_error": str(exc)}
    return {}


async def _startup_connectivity_probe(
    runtime: L0QuoteRuntime,
    *,
    strict_connectivity: bool,
    probe_symbol: str = "SPY.US",
) -> None:
    try:
        rows = await runtime.quote([probe_symbol])
    except Exception as exc:
        diagnostics = _runtime_diagnostics(runtime)
        profile = diagnostics.get("endpoint_profile")
        endpoint = diagnostics.get("endpoint_http_url")
        if strict_connectivity:
            raise RuntimeError(
                "startup connectivity probe failed for quote runtime: "
                f"profile={profile} endpoint={endpoint} error={exc}"
            ) from exc
        logger.warning(
            "[OpenApiBootstrap] Startup connectivity probe failed but strict gate disabled. "
            "profile=%s endpoint=%s error=%s",
            profile,
            endpoint,
            exc,
        )
        return
    diagnostics = _runtime_diagnostics(runtime)
    logger.info(
        "[OpenApiBootstrap] Startup connectivity probe passed: symbol=%s rows=%d profile=%s endpoint=%s",
        probe_symbol,
        len(rows),
        diagnostics.get("endpoint_profile"),
        diagnostics.get("endpoint_http_url"),
    )

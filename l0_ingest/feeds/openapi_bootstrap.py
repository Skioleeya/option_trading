"""OpenAPI runtime bootstrap helpers for L0 quote runtime wiring."""

from __future__ import annotations

import logging
import os
from typing import Any

from longport.openapi import Language

from l0_ingest.feeds.quote_runtime import L0QuoteRuntime

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
    mapping = {
        "en": Language.EN,
        "zh-cn": Language.ZH_CN,
        "zh-hk": Language.ZH_HK,
    }
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


def _dedupe_endpoint_profiles(
    profiles: list[dict[str, str]],
) -> list[dict[str, str]]:
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
    """Build ordered endpoint profiles for runtime connectivity fallback."""
    primary_http = _optional_text(getattr(cfg, "longport_http_url", None)) or _DEFAULT_HTTP_URL
    primary_quote_ws = (
        _optional_text(getattr(cfg, "longport_quote_ws_url", None)) or _DEFAULT_QUOTE_WS_URL
    )
    primary_trade_ws = (
        _optional_text(getattr(cfg, "longport_trade_ws_url", None)) or _DEFAULT_TRADE_WS_URL
    )

    profiles: list[dict[str, str]] = [
        {
            "name": "primary",
            "http_url": primary_http,
            "quote_ws_url": primary_quote_ws,
            "trade_ws_url": primary_trade_ws,
        }
    ]

    if "longbridge.com" in primary_http:
        profiles.append(
            {
                "name": "official_longportapp",
                "http_url": _convert_gateway(
                    primary_http,
                    "openapi.longbridge.com",
                    "openapi.longportapp.com",
                ),
                "quote_ws_url": _convert_gateway(
                    primary_quote_ws,
                    "openapi-quote.longbridge.com",
                    "openapi-quote.longportapp.com",
                ),
                "trade_ws_url": _convert_gateway(
                    primary_trade_ws,
                    "openapi-trade.longbridge.com",
                    "openapi-trade.longportapp.com",
                ),
            }
        )
    elif "longportapp.com" in primary_http:
        profiles.append(
            {
                "name": "official_longbridge",
                "http_url": _convert_gateway(
                    primary_http,
                    "openapi.longportapp.com",
                    "openapi.longbridge.com",
                ),
                "quote_ws_url": _convert_gateway(
                    primary_quote_ws,
                    "openapi-quote.longportapp.com",
                    "openapi-quote.longbridge.com",
                ),
                "trade_ws_url": _convert_gateway(
                    primary_trade_ws,
                    "openapi-trade.longportapp.com",
                    "openapi-trade.longbridge.com",
                ),
            }
        )
    else:
        profiles.append(
            {
                "name": "official_longportapp",
                "http_url": _DEFAULT_HTTP_URL,
                "quote_ws_url": _DEFAULT_QUOTE_WS_URL,
                "trade_ws_url": _DEFAULT_TRADE_WS_URL,
            }
        )
        profiles.append(
            {
                "name": "official_longbridge",
                "http_url": _LEGACY_HTTP_URL,
                "quote_ws_url": _LEGACY_QUOTE_WS_URL,
                "trade_ws_url": _LEGACY_TRADE_WS_URL,
            }
        )

    return _dedupe_endpoint_profiles(profiles)


def _longport_config_kwargs(cfg: Any) -> dict[str, Any]:
    """Build Config kwargs aligned with official Longport Rust SDK env contract."""
    return {
        "app_key": str(getattr(cfg, "longport_app_key")),
        "app_secret": str(getattr(cfg, "longport_app_secret")),
        "access_token": str(getattr(cfg, "longport_access_token")),
        "http_url": _optional_text(getattr(cfg, "longport_http_url", None)),
        "quote_ws_url": _optional_text(getattr(cfg, "longport_quote_ws_url", None)),
        "trade_ws_url": _optional_text(getattr(cfg, "longport_trade_ws_url", None)),
        "language": _resolve_language(getattr(cfg, "longport_language", None)),
        "enable_overnight": bool(getattr(cfg, "longport_enable_overnight", False)),
    }


def _sync_openapi_env_aliases(cfg: Any) -> dict[str, str]:
    """Expose config as BOTH LONGPORT_* and LONGBRIDGE_* env aliases."""

    def _set_pair(
        longport_key: str,
        longbridge_key: str,
        value: Any,
        out: dict[str, str],
    ) -> None:
        text = _optional_text(value)
        if text is None:
            return
        os.environ[longport_key] = text
        os.environ[longbridge_key] = text
        out[longport_key] = text
        out[longbridge_key] = text

    applied: dict[str, str] = {}
    _set_pair("LONGPORT_APP_KEY", "LONGBRIDGE_APP_KEY", getattr(cfg, "longport_app_key", None), applied)
    _set_pair("LONGPORT_APP_SECRET", "LONGBRIDGE_APP_SECRET", getattr(cfg, "longport_app_secret", None), applied)
    _set_pair("LONGPORT_ACCESS_TOKEN", "LONGBRIDGE_ACCESS_TOKEN", getattr(cfg, "longport_access_token", None), applied)
    _set_pair("LONGPORT_HTTP_URL", "LONGBRIDGE_HTTP_URL", getattr(cfg, "longport_http_url", None), applied)
    _set_pair("LONGPORT_QUOTE_WS_URL", "LONGBRIDGE_QUOTE_WS_URL", getattr(cfg, "longport_quote_ws_url", None), applied)
    _set_pair("LONGPORT_TRADE_WS_URL", "LONGBRIDGE_TRADE_WS_URL", getattr(cfg, "longport_trade_ws_url", None), applied)
    _set_pair("LONGPORT_LANGUAGE", "LONGBRIDGE_LANGUAGE", getattr(cfg, "longport_language", None), applied)

    overnight = bool(getattr(cfg, "longport_enable_overnight", False))
    os.environ["LONGPORT_ENABLE_OVERNIGHT"] = "true" if overnight else "false"
    os.environ["LONGBRIDGE_ENABLE_OVERNIGHT"] = "true" if overnight else "false"
    applied["LONGPORT_ENABLE_OVERNIGHT"] = os.environ["LONGPORT_ENABLE_OVERNIGHT"]
    applied["LONGBRIDGE_ENABLE_OVERNIGHT"] = os.environ["LONGBRIDGE_ENABLE_OVERNIGHT"]

    strict_connectivity = bool(getattr(cfg, "longport_startup_strict_connectivity", True))
    strict_text = "true" if strict_connectivity else "false"
    os.environ["LONGPORT_STARTUP_STRICT_CONNECTIVITY"] = strict_text
    os.environ["LONGBRIDGE_STARTUP_STRICT_CONNECTIVITY"] = strict_text
    applied["LONGPORT_STARTUP_STRICT_CONNECTIVITY"] = strict_text
    applied["LONGBRIDGE_STARTUP_STRICT_CONNECTIVITY"] = strict_text
    return applied


def _runtime_diagnostics(runtime: L0QuoteRuntime) -> dict[str, Any]:
    try:
        data = runtime.diagnostics()
        if isinstance(data, dict):
            return data
    except Exception as exc:  # pragma: no cover - defensive diagnostics path.
        return {"diagnostics_error": str(exc)}
    return {}


async def _startup_connectivity_probe(
    runtime: L0QuoteRuntime,
    *,
    strict_connectivity: bool,
    probe_symbol: str = "SPY.US",
) -> None:
    """Verify startup connectivity through quote REST before background loops start."""
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

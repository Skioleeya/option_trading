from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from longport.openapi import Language

from .._native_helpers import (
    build_endpoint_profiles_native,
    build_gateway_config_native,
)


def optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def resolve_language(value: Any) -> Any:
    if value is None or isinstance(value, Language):
        return value
    text = optional_text(value)
    if text is None:
        return None
    normalized = text.lower().replace("_", "-")
    resolved = {"en": Language.EN, "zh-cn": Language.ZH_CN, "zh-hk": Language.ZH_HK}.get(normalized)
    if resolved is None:
        return Language.EN
    return resolved


def normalize_endpoint_profiles(endpoint_profiles: list[dict[str, str]] | None) -> list[dict[str, str]]:
    if not endpoint_profiles:
        return []
    out: list[dict[str, str]] = []
    for idx, profile in enumerate(endpoint_profiles):
        if not isinstance(profile, dict):
            continue
        http_url = str(profile.get("http_url", "")).strip()
        quote_ws_url = str(profile.get("quote_ws_url", "")).strip()
        trade_ws_url = str(profile.get("trade_ws_url", "")).strip()
        if not http_url or not quote_ws_url or not trade_ws_url:
            continue
        out.append(
            {
                "name": str(profile.get("name", f"profile_{idx}")),
                "http_url": http_url,
                "quote_ws_url": quote_ws_url,
                "trade_ws_url": trade_ws_url,
            }
        )
    return out


def active_endpoint_profile(
    endpoint_profiles: list[dict[str, str]],
    active_idx: int,
) -> dict[str, str] | None:
    if not endpoint_profiles or active_idx >= len(endpoint_profiles):
        return None
    return endpoint_profiles[active_idx]


def gateway_ctor_args(config: dict[str, Any]) -> tuple[Any, ...]:
    return (
        config.get("app_key", ""),
        config.get("app_secret", ""),
        config.get("access_token", ""),
        config.get("http_url"),
        config.get("quote_ws_url"),
        config.get("trade_ws_url"),
        config.get("language"),
        bool(config.get("enable_overnight", False)),
    )


def rows_to_objects(rows: list[Any]) -> list[Any]:
    def to_object(value: Any) -> Any:
        if isinstance(value, dict):
            return SimpleNamespace(**{key: to_object(inner) for key, inner in value.items()})
        if isinstance(value, list):
            return [to_object(item) for item in value]
        return value

    return [to_object(row) for row in rows]


def index_name(value: Any) -> str:
    name = getattr(value, "name", None)
    if name:
        return str(name)
    text = str(value)
    return text.split(".")[-1] if "." in text else text


def build_openapi_endpoint_profiles(cfg: Any) -> list[dict[str, str]]:
    return build_endpoint_profiles_native(
        http_url=optional_text(getattr(cfg, "longport_http_url", None)),
        quote_ws_url=optional_text(getattr(cfg, "longport_quote_ws_url", None)),
        trade_ws_url=optional_text(getattr(cfg, "longport_trade_ws_url", None)),
    )


def longport_config_kwargs(cfg: Any) -> dict[str, Any]:
    gateway = build_gateway_config_native(
        app_key=str(getattr(cfg, "longport_app_key")),
        app_secret=str(getattr(cfg, "longport_app_secret")),
        access_token=str(getattr(cfg, "longport_access_token")),
        http_url=optional_text(getattr(cfg, "longport_http_url", None)),
        quote_ws_url=optional_text(getattr(cfg, "longport_quote_ws_url", None)),
        trade_ws_url=optional_text(getattr(cfg, "longport_trade_ws_url", None)),
        language=optional_text(getattr(cfg, "longport_language", None)),
        enable_overnight=bool(getattr(cfg, "longport_enable_overnight", False)),
    )
    return {
        "app_key": gateway["app_key"],
        "app_secret": gateway["app_secret"],
        "access_token": gateway["access_token"],
        "http_url": gateway["http_url"],
        "quote_ws_url": gateway["quote_ws_url"],
        "trade_ws_url": gateway["trade_ws_url"],
        "language": resolve_language(gateway["language"]),
        "enable_overnight": gateway["enable_overnight"],
    }

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any


def normalize_endpoint_profiles(
    endpoint_profiles: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    if not endpoint_profiles:
        return []
    normalized: list[dict[str, str]] = []
    for idx, profile in enumerate(endpoint_profiles):
        if not isinstance(profile, dict):
            continue
        http_url = str(profile.get("http_url", "")).strip()
        quote_ws_url = str(profile.get("quote_ws_url", "")).strip()
        trade_ws_url = str(profile.get("trade_ws_url", "")).strip()
        if not http_url or not quote_ws_url or not trade_ws_url:
            continue
        normalized.append(
            {
                "name": str(profile.get("name", f"profile_{idx}")),
                "http_url": http_url,
                "quote_ws_url": quote_ws_url,
                "trade_ws_url": trade_ws_url,
            }
        )
    return normalized


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


def decode_rows(payload: str) -> list[Any]:
    rows = json.loads(payload or "[]")
    if not isinstance(rows, list):
        raise RuntimeError("rust runtime payload is not a list")
    return rows_to_objects(rows)


def _to_object(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{key: _to_object(inner) for key, inner in value.items()})
    if isinstance(value, list):
        return [_to_object(item) for item in value]
    return value


def rows_to_objects(rows: list[Any]) -> list[Any]:
    return [_to_object(row) for row in rows]


def index_name(value: Any) -> str:
    name = getattr(value, "name", None)
    if name:
        return str(name)
    text = str(value)
    if "." in text:
        text = text.split(".")[-1]
    return text
